import api from '../lib/axios'


export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('files', file);

  const token = localStorage.getItem('token'); 
  const res = await api.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      Authorization: `Bearer ${token}`, 
    },
  });

  return res.data;
}
  
  export async function askQuestion(documentId: number, question?: string) {
    if (!question || !question.trim()) {
      throw new Error("Question can't be empty")
    }
  
    const payload = {
      documentId,
      question: question.trim(),
    }
  
    console.log('Payload:', { documentId, question })
    const res = await api.post('/chat', payload)
    return res.data
  }
  
  export async function fetchPdfPages(path: string) {
    const res = await api.post('/view-pdf', { path })
    return res.data.pages as { pageNumber: number; content: string }[]
  }

  export async function getAllDocuments() {
    const token = localStorage.getItem('token')
    const res = await api.get('/documents', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    return res.data
  }
  
  export async function deleteDocument(id: number) {
    const token = localStorage.getItem('token')
    const res = await api.delete(`/documents/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    return res.data
  }
  