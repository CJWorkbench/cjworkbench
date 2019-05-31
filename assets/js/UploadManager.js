import md5 from 'js-md5'
import { encode as base64encode } from 'base64-arraybuffer'

const MultipartMinimum = 5 * 1024 * 1024 // 5MB
const MultipartPartSize = 10 * 1024 * 1024 // 10MB

async function uploadUntilSuccess (uploadCallback) {
  while (true) {
    try {
      return await uploadCallback()
    } catch (err) {
      console.warn('Error during upload; restarting in 1s', err)
      await new Promise(resolve => setTimeout(resolve, 1000)) // sleep(1)
    }
  }
}

async function readBlobAsArrayBuffer (blob) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onError = () => reject(reader.error)
    reader.readAsArrayBuffer(blob)
  })
}

function base64Md5sumArrayBuffer (buffer) {
  const digest = md5.arrayBuffer(buffer)
  const base64 = base64encode(digest)
  return base64
}

/**
 * Begin uploading; return [abort, done].
 *
 * You must await `done` -- even if you call `abort()`.
 *
 * What happens next:
 *
 * * `onProgress(nBytesUploaded)` will be called periodically
 * * If `abort()` is called early enough, `onProgress(null)` will be
 *   called and `done` will resolve to `null`.
 * * If request completes, `done` will resolve to the `ETag` header value
 *   returned by S3 (stripped of quotation marks).
 * * Upon network error or non-200 response, `done` will be rejected
 *   with an Error.
 */
function startUpload (url, headers, blob, onProgress) {
  let abort
  const done = new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.responseType = 'text' // Avoid Firefox "XML Parsing Error: no root element found"
    xhr.upload.addEventListener('progress', (ev) => onProgress(ev.loaded))
    xhr.addEventListener('error', (ev) => {
      onProgress(null)
      reject(new Error('HTTP request error: ' + String(ev)))
    })
    xhr.addEventListener('abort', () => resolve(null))
    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        // BUG: https://github.com/minio/minio/issues/7492
        // ETag header won't show up on Firefox (because it doesn't
        // support Access-Control-Expose-Headers: *, and minio doesn't
        // write "ETag" specifically).
        //
        // For now: handle xhr.getResponseHEader('ETag') === null. Multipart
        // upload will break entirely; <5MB upload will work. This isn't a
        // regression -- it hasn't worked for months.
        const etag = (xhr.getResponseHeader('ETag') || 'minio-firefox-incompatible').replace('"', '')
        resolve(etag)
      } else {
        reject(new Error(`File server responded ${xhr.status} ${xhr.statusText}: ${xhr.responseText}`))
      }
    })
    xhr.open('PUT', url)
    for (const key in headers) {
      if (key === 'Content-Length') {
        // Don't set headers we aren't allowed to set. Luckily, AWS signature
        // doesn't include them.
        continue
      }
      xhr.setRequestHeader(key, headers[key])
    }
    xhr.send(blob)
    abort = () => xhr.abort()
  })

  // Don't worry: Promise ctor runs synchronously. `abort` is set.

  return [ abort, done ]
}

/**
 * Uploads to S3, signing requests via Websockets.
 */
export default class UploadManager {
  constructor (websocket) {
    this.websocket = websocket
    this.inProgress = {}  // wfModuleId => cancel callback
  }

  /**
   * Upload a file to S3 with presigned requests and notify the server.
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
    const method = file.size <= MultipartMinimum ? '_uploadSmall' : '_uploadMultipart'
    return await uploadUntilSuccess(() => this[method](wfModuleId, file, onProgress))
  }

  async _uploadSmall (wfModuleId, file, onProgress) {
    const buffer = await readBlobAsArrayBuffer(file)
    const base64Md5sum = base64Md5sumArrayBuffer(buffer)

    const { key, url, headers } = await this.websocket.callServerHandler('upload.prepare_upload', {
      wfModuleId,
      filename: file.name,
      nBytes: file.size,
      base64Md5sum: base64Md5sum
    })

    const [ abort, done ] = startUpload(url, headers, buffer, onProgress)
    this.inProgress[String(wfModuleId)] = abort
    let etag
    try {
      etag = await done // may raise Error
    } finally {
      delete this.inProgress[String(wfModuleId)]
    }
    if (etag === null) {
      // User aborted. Tell the server (so it can delete files); an error while
      // aborting is probably no big deal, so just log it and continue.
      await this.websocket.callServerHandler('upload.abort_upload', { wfModuleId, key }).catch(err => console.warn('Error aborting upload:', err))
      return null
    }

    const { uuid } = await this.websocket.callServerHandler('upload.complete_upload', { wfModuleId, key })

    return { uuid }
  }

  async _uploadMultipart (wfModuleId, file, onProgress) {
    // Set up what we do on abort
    let aborted = false
    const aborts = {} // partNumber => abort callback
    function abort () {
      aborted = true
      Object.values(aborts).forEach(f => f())
    }
    this.inProgress[String(wfModuleId)] = abort
    try {
      const { key, uploadId } = await this.websocket.callServerHandler(
        'upload.create_multipart_upload', {
          wfModuleId,
          filename: file.name
        }
      )
      if (aborted) return null

      const nParts = Math.ceil(file.size / MultipartPartSize) // also this is the last valid partNumber

      const partProgress = new Uint32Array(nParts) // partNumber-1 => nBytesUploaded, starting at 0
      function setPartProgress(partNumber, nBytesUploaded) {
        partProgress[partNumber - 1] = nBytesUploaded
        const nBytesTotal = partProgress.reduce(((acc, v) => acc + v), 0)
        onProgress(nBytesTotal)
      }
      if (aborted) return null

      const etags = new Array(nParts) // partNumber-1 => etag
      let nextPartNumber = 1
      /**
       * Worker: upload parts until `nextPartNumber > nParts`.
       *
       * Fills entries in `etags` such that it is an ordered list of ETags.
       *
       * Returns quickly when aborted; you can accelerate it by calling
       * `aborts[String(partNumber)]()`
       *
       * TODO throw error when we know a retry won't work, so we can restart
       * the entire upload starting at create_multipart_upload().
       */
      const work = async () => {
        while (!aborted && nextPartNumber <= nParts) {
          // Take the next "job" -- identified by partNumber
          const partNumber = nextPartNumber
          nextPartNumber++

          await uploadPart(partNumber)
        }
      }

      /**
       * Presign request and upload, retrying if needed, until etags[partNumber-1] is set.
       *
       * Returns quickly when aborted; you can accelerate it by calling
       * `aborts[String(partNumber)]()`
       *
       * TODO throw error when we know a retry won't work, so we can restart
       * the entire upload starting at create_multipart_upload().
       */
      const uploadPart = async (partNumber) => {
        const blob = file.slice(MultipartPartSize * (partNumber - 1), MultipartPartSize * partNumber)
        const nBytes = blob.size
        const buffer = await readBlobAsArrayBuffer(blob)
        const base64Md5sum = base64Md5sumArrayBuffer(buffer)

        // We'll keep retrying this part until abort or etag !== null.
        let etag = null
        while (!aborted && etag === null) {
          try {
            const { url, headers } = await this.websocket.callServerHandler(
              'upload.presign_upload_part', {
                wfModuleId,
                uploadId,
                partNumber,
                nBytes,
                base64Md5sum
              }
            )
            if (aborted) return
            const [ abort, done ] = startUpload(url, headers, buffer, (n) => setPartProgress(partNumber, n))
            aborts[String(partNumber)] = abort
            try {
              etag = await done // may raise Error
            } finally {
              delete aborts[String(partNumber)]
            }
            if (aborted) return
          } catch (err) {
            // TODO only retry on network failure; error in other cases
            console.log('Part upload failed; retrying in 1s', err)
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        }
        // Upload completed! We can move to the next partNumber now
        etags[partNumber - 1] = etag
      }

      // Spin up a number of workers -- they'll upload parts in parallel until
      // all parts are uploaded.
      await Promise.all([work(), work(), work()])
      if (aborted) return null

      let uuid = null
      while (!aborted && uuid === null) {
        try {
          const response = await this.websocket.callServerHandler(
            'upload.complete_multipart_upload', {
              wfModuleId,
              uploadId,
              etags
            }
          )
          uuid = response.uuid
        } catch (err) {
          // TODO only retry on network failure; error in other cases
          console.log('Complete failed; retrying in 1s', err)
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      }

      return { uuid }
    } finally {
      delete this.inProgress[String(wfModuleId)]
    }
  }

  /**
   * Cancel a pending upload, if there is one.
   */
  cancel (wfModuleId) {
    const cancel = this.inProgress[String(wfModuleId)]
    if (cancel) {
      delete this.inProgress[String(wfModuleId)]
      cancel()
      return Promise.resolve(null)
    } else {
      return Promise.resolve(null)
    }
  }
}
