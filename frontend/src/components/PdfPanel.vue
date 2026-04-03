<template>
    <div class="col-lg-6 col-md-12 overflow-auto pdf-panel">
      <div v-if="pdfPages.length" class="pdf-viewer-container">
        <div v-for="pageNumber in pdfPages" :key="pageNumber" class="pdf-page-container">
          <canvas :ref="el => setCanvasRef(el, pageNumber - 1)" class="pdf-page-canvas mb-3"></canvas>
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  defineProps<{
    pdfPages: number[]
    setCanvasRef: (el: unknown, index: number) => void
  }>()
  </script>
  
  <style scoped>
  .pdf-panel {
    max-height: 1000px;
    position: relative;
  }
  
  .pdf-viewer-container {
    background: #f0f0f0;
    padding: 10px;
  }
  
  .pdf-page-container {
    margin-bottom: 20px;
    box-shadow: 0 2px 5px rgba(0,0,0,.1);
    background: white;
  }
  
  .pdf-page-canvas {
    display: block;
    border: 1px solid #ddd;
    margin: 0 auto;
  }
  </style>