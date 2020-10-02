import S3 from 'aws-sdk/clients/s3'

/**
 * Uploads to S3, signing requests via Websockets.
 */
export default class UploadManager {
  constructor (websocket) {
    this.websocket = websocket
    this.inProgress = {} // stepId => cancel callback
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
   * * The server only tracks one file upload per Step -- there's no way
   *   for two users to upload concurrently. That makes `cancel()` straightforward.
   * * When completing, the server will send a Delta, adding the new files to the Step.
   * * The Promise returned will resolve to `{uuid: uuid}`; if the user aborts,
   *   it will resolve to `null`.
   * * `onProgress(nBytesUploaded)` will be called periodically.
   * * The Promise returned may be rejected on network error.
   */
  async upload (stepId, file, onProgress) {
    const filename = file.name
    const response = await this.websocket.callServerHandler('upload.create_upload', { stepId })
    const { region, bucket, key, endpoint, credentials } = response
    const s3 = new S3({
      apiVersion: '2006-03-01',
      endpoint,
      region,
      s3ForcePathStyle: true,
      credentials
    })

    const upload = s3.upload({
      Body: file,
      Bucket: bucket,
      Key: key,
      ContentLength: file.size
    })
    upload.on('httpUploadProgress', ({ loaded }) => onProgress(loaded))

    this.inProgress[String(stepId)] = async () => {
      upload.abort() // synchronous -- kicks off more requests
      try {
        await upload.promise()
      } catch {
        // it's caught elsewhere
      }
      await this.websocket.callServerHandler('upload.abort_upload', { stepId, key })
    }

    try {
      await upload.promise() // or throw error
    } catch (err) {
      if (err.code === 'RequestAbortedError') {
        return null // this isn't an error
      } else {
        throw err // present a pop-up to the user with this error we haven't yet figured out
      }
    }

    delete this.inProgress[String(stepId)]

    const finishResult = await this.websocket.callServerHandler('upload.finish_upload', {
      stepId,
      key,
      filename
    })
    return finishResult // { uuid }
  }

  /**
   * Cancel a pending upload, if there is one.
   */
  async cancel (stepId) {
    const cancel = this.inProgress[String(stepId)]
    if (cancel) {
      delete this.inProgress[String(stepId)]
      await cancel()
    }
  }
}
