<template>
    <footer class="footer-dark text-white py-5 mt-5">
      <div class="container text-center">
        <!-- Logo -->
        <a class="navbar-brand d-flex align-items-center justify-content-center gap-2 mb-4" href="#">
          <img src="/img/ai-logo.svg" alt="AIVA Logo" class="logo-img" />
          <span class="fw-bold fs-4">AIVA</span>
        </a>
  
        <!-- Navigation Links -->
        <div class="d-flex justify-content-center flex-wrap gap-4 mb-4">
          <a href="#" class="footer-link">Company</a>
          <a href="#" class="footer-link">Pricing</a>
          <a href="#" class="footer-link">Terms</a>
          <a href="#" class="footer-link">Privacy</a>
        </div>
  
        <!-- Social Icons -->
        <div class="d-flex justify-content-center gap-4 mb-4">
          <a href="#" class="text-white" aria-label="X / Twitter"><i class="bi bi-twitter-x"></i></a>
          <a href="#" class="text-white" aria-label="LinkedIn"><i class="bi bi-linkedin"></i></a>
          <a href="#" class="text-white" aria-label="YouTube"><i class="bi bi-youtube"></i></a>
        </div>
  
        <hr class="border-secondary my-4" />
  
        <!-- Bottom copyright -->
        <p class="small mb-0">&copy; {{ new Date().getFullYear() }} AIVA Technologies Inc. All rights reserved.</p>
      </div>
    </footer>
  </template>
  
<script setup>
</script>
  
<style scoped>
.footer-dark {
  background-color: rgb(33, 37, 41);
  min-height: 18.75em; 
  font-size: 1.5rem;
  padding-top: 2rem;
  padding-bottom: 2rem;
}

.logo-img {
  width: 3rem;
  height: 3rem;
}
  
.footer-link {
  color: rgb(225, 225, 225);
  font-weight: 600;
  text-decoration: none;
  padding: 0.2rem 0.5rem;
}
  
.footer-link:hover {
  text-decoration: none;
  color: rgb(223, 220, 220);
}
  
hr {
  opacity: 0.1;
}

@media (max-width: 768px) {
  .footer-dark {
    font-size: 0.95rem;
    padding-top: 1rem;
    padding-bottom: 1rem;
  }

  .logo-img {
    width: 2.5rem;
    height: 2.5rem;
  }

  .footer-link {
    font-size: 1rem;
  }

  p {
    font-size: 0.9rem;
  }
}
</style>