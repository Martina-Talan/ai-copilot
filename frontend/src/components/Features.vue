<template>
  <section class="features-section py-5 bg-light">
    <div class="container">
      <div class="text-center mb-5">
        <h3 class="features fw-bold mb-3">Features</h3>
        <h2 class="fw-bold mb-4 display-5">Process documents in seconds, not hours</h2>
        <p class="lead text-muted mx-auto">
          Let our AI read, analyze, and extract key information from your documents instantly.
        </p>
      </div>

      <div class="row align-items-center g-lg-5 g-4">
        <!-- Left Features Column -->
        <div class="col-xl-3 col-lg-4 col-md-6">
          <div class="feature-card p-4 h-100 mb-4">
            <div class="d-flex flex-column">
              <h3 class="h4 fw-bold mb-3">No upload limits</h3>
              <p class="mb-0">
                Upload as many files as you want. AIVA handles large documents fast, with no waiting and no limits.
              </p>
            </div>
          </div>

          <div class="feature-card p-4 h-100 mt-4">
            <div class="d-flex flex-column">
              <h3 class="h4 fw-bold mb-3">Smart answers</h3>
              <p class="mb-0">
                Ask anything — once or many times. AIVA responds instantly, with real-time context and clarity.
              </p>
            </div>
          </div>
        </div>

        <!-- Center Mockup -->
        <div class="col-xl-6 col-lg-4 col-md-12 text-center order-first order-lg-0 px-lg-5">
          <img src="/img/mobile.png" class="img-fluid mockup" alt="Document AI interface">
        </div>

        <!-- Right Features Column -->
        <div class="col-xl-3 col-lg-4 col-md-6">
          <div class="feature-card p-4 h-100 mb-4">
            <div class="d-flex flex-column">
              <h3 class="h4 fw-bold mb-3">Source Highlights</h3>
              <p class="mb-0">
                See where each answer comes from. AIVA links results directly to the exact part of your document for full clarity.
              </p>
            </div>
          </div>

          <div class="feature-card p-4 h-100 mt-4">
            <div class="d-flex flex-column">
              <h3 class="h4 fw-bold mb-3">Easy to embed</h3>
              <p class="mb-0">
                Add AIVA to your site in seconds. Just paste a snippet — no coding or setup needed anywhere.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lead {
  max-width: 50rem;
}

.features {
  text-transform: uppercase;
  color: rgb(133, 102, 82);
}

.features-section {
  position: relative;
}

.feature-card {
  background: rgb(255, 255, 255);
  border-radius: 0.75rem; 
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.05); 
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-0.3125rem);
  box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.1); 
}

.mockup {
  max-width: 100%;
  filter: drop-shadow(0 0.625rem 1.25rem rgba(0, 0, 0, 0.1)); 
  max-height: 37.5rem; 
}

.feature-card p {
    font-size: 1.5rem
  }

/* XL screens (≥1200px) */
@media (min-width: 1200px) {
  .mockup {
    max-height: 43.75rem;
  }

  .feature-card {
    padding: 2rem;
  }

  .lead {
    font-size: 1.8rem;
  }
}

/* LG screens (992px–1199px) */
@media (min-width: 992px) and (max-width: 1199.98px) {
  .mockup {
    max-height: 40.625rem; 
  }
}

/* MD screens (768px–991px) */
@media (min-width: 768px) and (max-width: 991.98px) {
  .mockup {
    max-height: 31.25rem; 
    margin: 2rem 0;
  }

  .container h2 {
    font-size: 2rem;
  }

  .lead, .feature-card h3 {
    font-size: 1.5rem;
  }

  .feature-card p {
    font-size: 1.2rem
  }
}

/* SM screens (≤767px) */
@media (max-width: 767.98px) {
  .mockup {
    max-height: 28.125rem;
    margin: 2rem 0;
  }

  .row > div {
    order: 0;
  }

  .feature-card {
    margin-bottom: 1.5rem;
  }

  .feature-card:last-child {
    margin-bottom: 0;
  }

  .container h2 {
    font-size: 1.75rem;
  }

  .lead, .feature-card h3 {
    font-size: 1.25rem;
  }

  .feature-card p {
    font-size: 1rem
  }
}
</style>