<template>
    <section class="hero-section position-relative w-100 overflow-hidden">
    <!-- Navbar -->
    <Navbar class="position-absolute top-0 start-0 end-0 z-3 w-100" />

    <!-- Backgroundvideo -->
    <video
      ref="heroVideo"
      autoplay
      muted
      loop
      playsinline
      class="hero-video position-absolute top-0 start-0 w-100 h-100 object-fit-cover"
    >
      <source src="/img/video.mp4" type="video/mp4" />
      Your browser does not support videos
    </video>

    <!-- Texts -->
    <div
      class="hero-content position-relative d-flex flex-column justify-content-center align-items-center h-100 text-white text-center"
    >
      <h3 class="fw-bold mb-4">AI Copilot for your documents</h3>
      <p ref="target" class="animated-text mb-5"></p>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Navbar from '../components/Navbar.vue'
import Writer from 't-writer.js'

const heroVideo = ref(null)
const target = ref(null)

onMounted(() => {
  if (heroVideo.value) {
    heroVideo.value.playbackRate = 0.6
  }

  if (target.value) {
    const writer = new Writer(target.value, {
      loop: true,
      typeColor: '#fff',
      typeSpeed: 80,
      deleteSpeed: 40,
    })

    writer
      .type('Analyze your files')
      .rest(1200)
      .clear()
      .type('Summarize your documents')
      .rest(1200)
      .clear()
      .type('Extract key insights')
      .rest(1200)
      .clear()
      .start()
    }
})
</script>

<style scoped>
.hero-section {
  height: 56rem;
}

.hero-video {
  filter: brightness(0.5);
  z-index: 0;
}

.hero-content {
  z-index: 2;
}

.object-fit-cover {
  object-fit: cover;
}

.start-link {
  color: rgb(179, 137, 110);
  border-color: rgb(179, 137, 110);
  background-color: transparent;
  text-decoration: none;
}

.start-link:hover {
  background-color: rgb(179, 137, 110);
  color: rgb(255, 255, 255);
  border-color: rgb(179, 137, 110);
}

.animated-text {
  font-size: 3.5rem;
  font-weight: 600;
  line-height: 1.2;
}
/* Responsive */
@media (max-width: 991.98px) {
  .hero-content h3 {
    font-size: 1.5rem;
  }

  .animated-text {
    font-size: 2.25rem;
  }
}

@media (max-width: 767.98px) {
  .hero-content h3 {
    font-size: 1.25rem;
  }

  .animated-text {
    font-size: 2rem;
  }
}

@media (max-width: 575.98px) {
  .hero-content h3 {
    font-size: 1rem;
  }

  .animated-text {
    font-size: 1.75rem;
  }
}
</style>
