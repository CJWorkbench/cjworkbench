import S3 from 'aws-sdk/clients/s3'

/**
 * Uploads to S3, signing requests via Websockets.
 */
export default class UploadManager {
  constructor (websocket) {
    this.websocket = websocket
    this.inProgress = {} // wfModuleId => cancel callback
  }

  /**
   * Upload a file to S3 and notify the Workbench server.
   *
   * The steps:
   *
   * 1. Client (that's us!) asks Server (Workbench) to allocate an upload
   * 2. Server responds with request-specific S3 auth info
   * 3. Client starts uploading to S3 -- and registers a cancel callback in this.inProgress.
   * 4. Client finishes uploading
   *
   * There are two main upload paths:
   *
   * A. For files smaller than or equal to 5MB:
   *     a. `upload.prepare_upload()` to generate presigned url+headers
   *     b. upload to S3 with url+headers
   *     c. `upload.complete_upload()` to notify server of new file
   * B. For files over 5MB:
   *     a. `upload.prepare_multipart_upload()` to start an upload session
   *     b. `upload.presign_upload_part()` and PUT each chunk of the file
   *     c. `upload.complete_multipart_upload()` to notify server and build file
   *
   * Both these paths share some traits:
   *
   * * The server only tracks one file upload per WfModule -- there's no way
   *   for two users to upload concurrently. That makes `cancel()`
   *   straightforward.
   * * When completing, the server will send a Delta, adding the new files to
   *   the WfModule.
   * * The Promise returned will resolve to `{uuid: uuid}`; if the user aborts,
   *   it will resolve to `null`.
   * * The Promise returned will never be rejected. It'll retry forever.
   * * `onProgress(nBytesUploaded)` will be called periodically.
   */
  async upload (wfModuleId, file, onProgress) {
    const filename = file.name
    const response = await this.websocket.callServerHandler('upload.create_upload', { wfModuleId })
    const { region, bucket, key, endpoint, credentials } = response
    const s3 = new S3({
      apiVersion: '2006-03-01',
      endpoint,
      region,
      s3ForcePathStyle: true,
      credentials
    })

    const uploadResult = await new Promise((resolve, reject) => {
      const request = s3.putObject({
        Body: file,
        Bucket: bucket,
        Key: key,
        ContentLength: file.size
      }, (err, data) => {
        if (err) {
          return reject(err)
        } else {
          return resolve(data)
        }
      })
      this.inProgress[String(wfModuleId)] = async () => {
        request.abort()
        try {
          await uploadResult
        } catch {
          // ignore -- we know there's an error
        }
        await this.websocket.callServerHandler('upload.abort_upload', { wfModuleId, key })
      }
    })

    delete this.inProgress[String(wfModuleId)]

    const finishResult = await this.websocket.callServerHandler('upload.finish_upload', {
      wfModuleId,
      key,
      filename
    })
    console.log(finishResult)
    return finishResult // { uuid }
  }

  /**
   * Cancel a pending upload, if there is one.
   */
  async cancel (wfModuleId) {
    const cancel = this.inProgress[String(wfModuleId)]
    if (cancel) {
      delete this.inProgress[String(wfModuleId)]
      await cancel()
    }
  }
}
