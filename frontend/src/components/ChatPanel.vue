<template>
    <div class="col-lg-6 col-md-12 d-flex flex-column pe-lg-4 chat-panel">
      <button @click="$emit('back')" class="btn btn-brown mt-3 mb-5" title="Back to list">
        <i class="bi bi-arrow-left"></i> Go back
      </button>
  
      <div class="chat-content flex-grow-1 overflow-auto">
        <div v-for="(msg, i) in history" :key="i" class="chat-row">
          <div class="avatar">
            <span v-if="msg.role === 'user'" class="user-avatar">{{ userInitial }}</span>
            <img v-else src="/img/ai-logo.svg" alt="AI" class="bot-avatar" />
          </div>
  
          <div class="chat-message">
            <p class="mt-1">{{ msg.content }}</p>
  
            <div v-if="msg.role === 'assistant' && msg.sources?.length" class="source-inline">
              <p class="source-item">
                Pages:
                <span v-for="(src, index) in msg.sources" :key="index">
                  {{ src.pageNumber }}
                  <span v-if="(index as number) < msg.sources.length - 1">, </span>
                </span>
              </p>
            </div>
          </div>
        </div>
  
        <div v-if="isStreaming" class="chat-row">
          <div class="avatar">
            <img src="/img/ai-logo.svg" alt="AI" class="bot-avatar" />
          </div>
          <div class="chat-message mt-1">
            <p>
              {{ answer?.contextAnswer }}
              <span v-if="!answer?.contextAnswer" class="typing-indicator">
                <span></span><span></span><span></span>
              </span>
            </p>
          </div>
        </div>
  
        <div v-if="!isStreaming && answer?.additionalInfo" class="mt-3 p-3 bg-light rounded">
          <p>{{ answer.additionalInfo }}</p>
        </div>
  
        <div v-if="error" class="mt-4 p-3 bg-danger bg-opacity-10 text-danger rounded">
          {{ error }}
        </div>
  
        <div ref="chatEndRef"></div>
      </div>
  
      <form @submit.prevent="submitQuestion" class="chat-input-wrapper">
        <div class="d-flex">
          <input
            v-model="question"
            type="text"
            placeholder="Ask ..."
            class="form-control rounded-start custom-input mb-5"
          />
          <button
            type="submit"
            class="btn mb-5"
            :class="['btn-brown', loading || !question.trim() ? 'disabled' : '']"
            style="border-top-left-radius: 0; border-bottom-left-radius: 0;"
          >
            <i class="bi bi-send"></i>
          </button>
        </div>
      </form>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, watch } from 'vue'
  import type { ChatAnswer } from '../types/chat-types'
  
  const props = defineProps<{
    history: any[]
    userInitial: string
    loading: boolean
    isStreaming: boolean
    answer: ChatAnswer
    error: string
  }>()
  
  const emit = defineEmits<{
    (e: 'back'): void
    (e: 'ask', question: string): void
  }>()
  
  const question = ref('')
  const chatEndRef = ref<HTMLElement | null>(null)
  
  const scrollToBottom = () => {
    setTimeout(() => chatEndRef.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }), 50)
  }
  
  const submitQuestion = () => {
    if (!question.value.trim()) return
    emit('ask', question.value)
    question.value = ''
  }
  
  watch(
    () => props.answer?.contextAnswer,
    () => {
      scrollToBottom()
    }
  )
  
  defineExpose({ scrollToBottom })
  </script>
  
  <style scoped>
  .chat-content {
    padding: 0 1rem;
  }

  .chat-panel > button {
    margin-left: 1rem;
  }

  .chat-panel {
    height: 100%;
    min-height: 0;
  }

  p { 
    color: black;
  }
  
  .typing-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    margin-left: 0.5rem;
  }
  .typing-indicator span {
    width: 0.5rem;
    height: 0.5rem;
    background-color: rgb(179,137,110);
    border-radius: 50%;
    animation: bounce 1.2s infinite ease-in-out;
  }
  .typing-indicator span:nth-child(2) { 
    animation-delay: .2s; 
  }
  .typing-indicator span:nth-child(3) { 
    animation-delay: .4s; 
  }
  
  @keyframes bounce {
    0%,80%,100% { transform: translateY(0); }
    40% { transform: translateY(-6px); }
  }
  
  .btn-brown { 
    background: rgb(179,137,110); 
    color: white; 
    border: none; 
    width: 7.5rem; 
  }

  .btn-brown:hover { 
    background: rgb(113,85,69); 
  }
  
  .form-control:focus {
    outline: none;
    box-shadow: none;
    border-color: rgb(179,137,110);
  }
  
  .custom-input {
    height: 3.125rem;
    font-size: 1.1rem;
    padding: 0.625rem 1rem;
  }
  
  .chat-row {
    display: flex;
    align-items: flex-start;
    gap: 0.625rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid rgb(204 204 204);
  }

  .chat-input-wrapper {
    padding: 0.75rem 1rem 1rem 1rem;
    border-top: 1px solid rgb(238 238 238);
  }
  
  .avatar { 
    flex-shrink: 0; 
    width: 2rem; 
    height: 2rem; 
  }
  
  .user-avatar {
    width: 2rem;
    height: 2rem;
    background: rgb(179 137 110);
    color: white;
    font-weight: bold;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
  }
  
  .bot-avatar {
    width: 2rem;
    height: 2rem;
    border-radius: 0;
    object-fit: contain;
    filter: invert(61%) sepia(39%) saturate(532%) hue-rotate(339deg) brightness(90%) contrast(85%);
    background: transparent;
  }
  
  .source-inline { 
    margin-top: 1rem; 
  }

  .source-item { 
    margin: 0; 
    padding: 0; 
    font-size: 0.9rem; 
    color: rgb(102 102 102); 
  }

  ::placeholder { 
    color: rgb(161,160,160); 
    opacity: 1; 
  }
  </style>