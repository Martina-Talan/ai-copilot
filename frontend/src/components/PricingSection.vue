<template>
  <section class="bg-white text-center py-5 px-3">
    <h2 class="fw-bold display-5 mb-3">Free to start. Cheap to scale.</h2>
    <p class="text-muted mb-5">Simple pricing that grows with you.</p>

    <div class="custom-container">
      <div class="row g-4">
        <div
          class="col-12 col-sm-6 col-lg-3"
          v-for="(plan, i) in plans"
          :key="i"
        >
          <div class="card pricing-card h-100 d-flex flex-column text-start">
            <div class="card-body d-flex flex-column justify-content-between p-4">
              <div>
                <h3 class="fw-bold mb-3">{{ plan.name }}</h3>
                <p class="fw-bold mb-0 custom-price">{{ plan.price }}</p>
                <p v-if="plan.sub" class="text-muted mb-3">{{ plan.sub }}</p>
                <ul class="feature-list mb-4">
                  <li v-for="(item, idx) in plan.features" :key="idx">
                    ✔️ {{ item }}
                  </li>
                </ul>
              </div>
              <button class="btn btn-brown w-100 mt-auto">Get started</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <p class="text-muted mt-5 text-center">
  Looking to scale past 10 users? <a href="#" class="text-decoration-underline fw-bold custom-text">Chat with sales</a>
</p>
  </section>
</template>


<script setup>
const plans = [
  {
    name: 'Free',
    price: '$0',
    sub: '',
    features: ['Access to basic features', 'Up to 60 pages', 'Up to 10 answers'],
  },
  {
    name: 'Student',
    price: '$1.99',
    sub: 'per month',
    features: ['Access to basic features', 'Up to 200 free pages', '$0.02 per additional page', 'Basic chat support'],
  },
  {
    name: 'Expert',
    price: '$9.99',
    sub: 'per month',
    features: ['Access to basic features', 'Up to 500 free pages', '$0.02 per additional page', '3 users included', 'Premium chat support', 'Uses GPT 4.0 model'],
  },
  {
    name: 'Team',
    price: '$49',
    sub: 'per user per month',
    features: ['Access to basic features', 'Up to 5,000 free pages', '$0.01 per additional page', '10 users included', 'Premium chat support', 'Uses GPT 4.0 model', 'OCR images & scanned text', 'Response personalization'],
  },
];
</script>

<style scoped>
.custom-container {
  max-width: 131.25rem;
  padding-left: 3.13rem;
  padding-right: 3.13rem;
  margin: 0 auto;
}

.pricing-card {
  border: none;
  box-shadow: 0 0.5rem 1.2rem rgba(0, 0, 0, 0.08);
  border-radius: 1rem;
  min-height: 40rem;
  transition: all 0.3s ease;
}

.pricing-card:hover {
  box-shadow: 0 1rem 2rem rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
}

.custom-price {
  font-size: 3rem;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin-top: 1.5rem;
}

.feature-list li {
  font-size: 1.35rem;
  margin: 0.8rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgb(74, 74, 74);
  ;
}

.btn-brown {
  background-color: rgb(179, 137, 110);
  color: rgb(255, 255, 255);
  font-weight: 600;
  border-radius: 0.38rem;
  transition: background-color 0.3s ease;
  padding: 1rem 1.5rem;
  font-size: 1.2rem;
}

.btn-brown:hover {
  background-color: rgb(133, 102, 82);
}

p {
font-size: 1.8rem;
}

.custom-text{
  color:rgb(133, 102, 82);
}

@media (max-width: 991.98px) {
  .custom-container {
    padding: 0 1.5rem;
  }

  h2.display-5 {
    font-size: 2rem;
  }

  p {
    font-size: 1.5rem;
  }

  .card-body h3 {
    font-size: 1.5rem;
  }

  .custom-price {
    font-size: 2rem;
  }

  .feature-list li {
    font-size: 1.2rem;
    margin: 0.5rem 0;
  }

  .btn-brown {
    font-size: 1rem;
    padding: 0.8rem 1rem;
  }
}

@media (max-width: 768px) {
  h2.display-5 {
    font-size: 1.75rem;
  }

  p {
    font-size: 1.2rem;
  }

  .card-body h3 {
    font-size: 1.2rem;
  }

  .custom-price {
    font-size: 1.5rem;
  }

  .feature-list li {
    font-size: 1rem;
  }
}

</style>
