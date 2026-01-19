// Cấu hình NLP service endpoint
// Đổi giá trị này để switch giữa Ollama (local) và FPT (cloud)

export const NLP_CONFIG = {
  // 'ollama' = Local Ollama service (port 8000)
  // 'fpt' = FPT Qwen service (port 8001)
  provider: 'fpt' as 'ollama' | 'fpt',
  
  endpoints: {
    ollama: '/api/nlp/chat',
    fpt: '/api/nlp-fpt/chat'
  },
  
  // Helper để lấy endpoint hiện tại
  getCurrentEndpoint() {
    return this.endpoints[this.provider]
  }
}

// Export default endpoint
export const NLP_ENDPOINT = NLP_CONFIG.getCurrentEndpoint()
