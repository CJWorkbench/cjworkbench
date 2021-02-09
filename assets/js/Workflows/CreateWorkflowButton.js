import React, { useState } from 'react'
import { csrfToken } from '../utils'

function CreateWorkflowButton ({ children }) {
  const [isSubmitted, setSubmitted] = useState(false)

  return (
    <form className='create-workflow' method='post' action='/workflows' onSubmit={() => setSubmitted(true)}>
      <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
      <button type='submit' disabled={isSubmitted}>
        {children}
      </button>
    </form>
  )
}
export default CreateWorkflowButton
