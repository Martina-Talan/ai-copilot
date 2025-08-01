<template>
  <div class="container-fluid px-0">
    <div class="row g-0 min-vh-100 d-flex">
      <!-- Left -->
      <div class="col-lg-6 d-flex flex-column justify-content-between bg-light p-5">
        <div>
          <div class="d-flex align-items-center gap-2 mb-4">
            <img src="/img/ai-logo.svg" alt="Logo" class="aiva-logo" />
            <span class="fw-bold aiva-accent">AIVA</span>
          </div>
        </div>

          <!-- Center -->
        <div class="text-center d-flex flex-column align-items-center justify-content-center">
          <p class="h3 text-dark mb-4 aiva-testimonial">
            I love AIVA because it helps researchers and professionals extract answers and insights faster than ever before.
          </p>
          
        <div class="text-warning mb-3 star-rating">
          <i class="bi bi-star-fill me-1"></i>
          <i class="bi bi-star-fill me-1"></i>
          <i class="bi bi-star-fill me-1"></i>
          <i class="bi bi-star-fill me-1"></i>
          <i class="bi bi-star-fill"></i>
        </div>
  
        <div class="d-flex flex-column align-items-center">
            <img src="/img/user-1.jpg" alt="User photo" class="rounded-circle mb-2 user-photo mb-3" />
            <p class="h4 fw-semibold text-dark mb-3 user-name">Selena Walter</p>
            <p class="h5 text-muted user-data">Product Lead | MedTech Group</p>
          </div>
        </div>

        <!-- Copyright -->
        <div class="h5 text-muted text-start mt-5 copyright">
          © 2025 AIVA Technologies Inc.
        </div>
      </div>

      <!-- Right -->
      <div class="col-lg-6 d-flex justify-content-center align-items-center bg-white p-5">
        <div class="w-100 form-wrapper">
          <h2 class="display-5 fw-bold text-dark mb-3">Welcome back</h2>
          <p class="login-text text-muted mb-5">Please enter your credentials to continue.</p>

          <form @submit.prevent="handleLogin" class="vstack gap-4">
            <input
              v-model="email"
              type="email"
              placeholder="Enter your email"
              class="form-control form-control-lg input-lg-custom"
              required
            />
            <input
              v-model="password"
              type="password"
              placeholder="Enter your password"
              class="form-control form-control-lg input-lg-custom mb-4"
              required
            />
            <button type="submit" class="btn btn-lg text-white w-100 btn-brown">
              Sign in
            </button>
            <p v-if="errorMessage" class="text-danger small mt-2">{{ errorMessage }}</p>
          </form>

          <p class="login-text text-center text-muted mt-5">
            Don’t have an account?
            <router-link to="/register" class="text-decoration-none fw-semibold text-custom">
              Sign up
            </router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const router = useRouter()
const userStore = useUserStore()

const handleLogin = async () => {
  try {
    const response = await axios.post('http://localhost:3000/auth/login', {
      email: email.value,
      password: password.value,
    })

    const token = response.data.access_token
    localStorage.setItem('token', token)
    userStore.setToken(token)
    router.push('/dashboard')
  } catch (err) {
    errorMessage.value = 'Login failed. Please check your data.'
  }
}
</script>

<style scoped>
.testimonial-text {
  max-width: 31.25rem;
}

.login-text{
  font-size: 1.4rem;
}

.user-photo {
  width: 5rem;
  height: 5rem;
}

.form-wrapper {
  max-width: 31.25rem;
}

.btn-brown {
  background-color: rgb(185, 137, 110);
  font-size: 1.5rem;
  padding: 0.8rem 1rem;
  border: none;
}

.btn-brown:hover {
  background-color: rgb(133, 102, 82);
}

.input-lg-custom {
  font-size: 1.2rem;
  padding: 0.8rem 1rem;
}

.input-lg-custom:focus {
  outline: none; 
  box-shadow: none; 
  border-color: rgb(179, 137, 110); 
  box-shadow: 0 0 0 0.2rem rgba(179, 137, 110, 0.25);
}

.aiva-logo {
  height: 3rem;
  filter: invert(61%) sepia(39%) saturate(532%) hue-rotate(339deg) brightness(90%) contrast(85%);
}

.aiva-accent {
  color: rgb(133, 102, 82);
  font-size: 2rem;
}

.text-custom{
  color:rgb(179, 137, 110);
}

.text-custom:hover{
  color: rgb(133, 102, 82);
}

@media (max-width: 991.98px) {
  .login-text {
    font-size: 1.2rem;
  }

  .form-wrapper {
    padding: 1rem;
  }

  .btn-brown {
    font-size: 1.2rem;
    padding: 0.6rem 0.8rem;
  }

  .input-lg-custom {
    font-size: 1rem;
    padding: 0.6rem 0.8rem;
  }

  .aiva-logo {
    font-size: 3rem;
  }

  .aiva-accent {
    font-size: 2rem;
  }

  .aiva-testimonial {
    font-size: 1.2rem;
    max-width: 100%;
  }

  .star-rating {
    font-size: 1.2rem;
  }

  .copyright {
    font-size: 1rem;
  }

  .user-photo {
    width: 4rem;
    height: 4rem;
  }

  .user-name {
    font-size: 1rem;
  }

  .user-data {
    font-size: 1rem;
  }
}

@media (max-width: 768px) {
  .btn-brown {
    font-size: 1rem;
  }

  .aiva-accent {
    font-size: 1.8rem;
  }

  .form-wrapper {
    padding: 0.5rem;
  }

  .login-text {
    font-size: 1rem;
  }

  .aiva-testimonial {
    font-size: 1rem;
    padding: 0 1rem;
  }

  .star-rating {
    font-size: 1rem;
  }


  .copyright {
    font-size: 1rem;
  }
}

@media (max-width: 576px) {
  .form-wrapper {
    max-width: 100%;
  }

  .display-5 {
    font-size: 1.5rem;
  }

  .aiva-accent {
    font-size: 1.5rem;
  }

  .star-rating {
    font-size: 0.8rem;
  }

  .copyright {
    font-size: 0.8rem;
  }

  .input-lg-custom {
    font-size: 0.95rem;
    padding: 0.5rem 0.75rem;
  }

  .btn-brown {
    font-size: 0.95rem;
    padding: 0.5rem 0.75rem;
  }
}
</style>
