<template>
  <section class="ask-section text-center py-5 px-3">
    <h2 class="fw-bold display-5 mb-4">
      Get instant answers from all your documents
    </h2>
    <p class="text-muted mb-5">
      Let our AI read your files and give you clear, reliable answers.
    </p>

    <!-- Caroseul -->
    <div id="fileCarousel" class="carousel slide carousel-dark" data-bs-ride="carousel">
      <div class="carousel-inner">
        <div class="carousel-item active">
          <img src="/img/screenshot.png" class="d-block w-100 rounded shadow" alt="Slide 1">
        </div>
        <div class="carousel-item">
          <img src="/img/screenshot.png" class="d-block w-100 rounded shadow" alt="Slide 2">
        </div>
        <div class="carousel-item">
          <img src="/img/screenshot.png" class="d-block w-100 rounded shadow" alt="Slide 3">
        </div>
      </div>
    </div>

    <div class="carousel-indicators-custom mt-4">
      <button type="button" data-bs-target="#fileCarousel" data-bs-slide-to="0" class="active" aria-current="true" aria-label="Slide 1"></button>
      <button type="button" data-bs-target="#fileCarousel" data-bs-slide-to="1" aria-label="Slide 2"></button>
      <button type="button" data-bs-target="#fileCarousel" data-bs-slide-to="2" aria-label="Slide 3"></button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  const carousel = document.querySelector('#fileCarousel');
  const indicators = document.querySelectorAll('.carousel-indicators-custom button');

  if (carousel) {
    carousel.addEventListener('slid.bs.carousel', function (event: any) {
      indicators.forEach((btn) => btn.classList.remove('active'));
      indicators[event.to].classList.add('active');
    });
  }
});
</script>

<style scoped>
p{
  font-size: 1.5rem;
}

.carousel-inner img {
  max-width: 64rem;
  margin-left: auto;
  margin-right: auto;
  border: 5px solid rgb(133, 102, 82);
  border-radius: 0.625rem; 
}

.carousel-indicators-custom {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
}

.carousel-indicators-custom button {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background-color: rgb(0, 0, 0);
  opacity: 0.5;
  border: none;
}

.carousel-indicators-custom button.active {
  opacity: 1;
  background-color: rgb(133, 102, 82);
}

@media (max-width: 991.98px) {
  .ask-section h2 {
    font-size: 2rem;
  }

  .ask-section p {
    font-size: 1.25rem; 
  }
}

@media (max-width: 767.98px) {
  .ask-section h2 {
    font-size: 1.75rem;
  }

  .ask-section p {
    font-size: 1.125rem;
  }
}

@media (max-width: 575.98px) {
  .ask-section h2 {
    font-size: 1.5rem;
  }

  .ask-section p {
    font-size: 1rem;
  }
}
</style>
  