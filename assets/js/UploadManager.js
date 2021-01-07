import { Upload } from 'tus-js-client'

/**
 * Uploads to S3, signing requests via Websockets.
 */
export default class UploadManager {
  constructor (websocket) {
    this.websocket = websocket
    this.inProgress = {} // stepId => tus.Upload
  }

  /**
   * Upload a file to S3 and notify the Workbench server.
   *
   * The steps:
   *
   * 1. Client (that's us!) asks Server (Workbench) to allocate an upload
   * 2. Server responds with tusUploadUrl
   * 3. Client starts uploading to tusUploadUrl -- writing this.inProgress.
   * 4. Client finishes uploading
   *
   * * We only store one Upload per Step.
   * * When completing (before step 4 finishes), the server will send a Delta,
   *   adding the new files to the Step.
   * * `onProgress(nBytesUploaded)` will be called periodically.
   * * The Promise returned may be rejected on network error.
   */
  async upload (stepSlug, file, onProgress) {
    const filename = file.name
    const size = file.size

    const response = await this.websocket.callServerHandler('upload.create_upload', { stepSlug, filename, size })
    const { tusUploadUrl } = response

    const promise = new Promise((resolve, reject) => {
      const upload = new Upload(file, {
        uploadUrl: tusUploadUrl,
        onProgress,
        onSuccess: resolve,
        onError: reject
      })
      this.inProgress[stepSlug] = upload
      upload.start()
    })

    try {
      await promise // or throw error
    } catch (err) {
      if (err.code === 'RequestAbortedError') {
        return null // this isn't an error
      } else {
        throw err // present a pop-up to the user with this error we haven't yet figured out
      }
    }

    delete this.inProgress[stepSlug]
  }

  /**
   * Cancel a pending upload, if there is one.
   */
  async cancel (stepSlug) {
    const upload = this.inProgress[stepSlug]
    if (upload) {
      await upload.abort(true)
    }
  }
}
