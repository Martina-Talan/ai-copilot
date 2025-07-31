<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark px-4 py-3">
    <div class="container-lg">
      <!-- Logo -->
      <a class="navbar-brand d-flex align-items-center gap-2 logo" href="#">
        <img src="/img/ai-logo.svg" alt="AIVA Logo" class="logo-img" />
        <span class="fw-bold fs-2">AIVA</span>
      </a>

      <!--  Toggler -->
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#mainNavbar"
        aria-controls="mainNavbar"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>

      <!-- Left -->
      <div class="collapse navbar-collapse" id="mainNavbar">
        <ul class="navbar-nav me-auto mb-lg-0">
          <li class="nav-item links-left mt-2">
            <router-link to="/dashboard" class="nav-link links">Dashboard</router-link>
          </li>
          <li class="nav-item links-left mt-2">
            <router-link to="/upload" class="nav-link links">Upload</router-link>
          </li>
          <li class="nav-item links-left mt-2">
            <router-link to="/chat" class="nav-link links">Chat</router-link>
          </li>
        </ul>

        <!-- Right -->
        <div class="d-flex links-right gap-3">
          <router-link to="/login" class="btn btn-outline-light login">Login</router-link>
          <router-link to="/register" class="btn btn-light text-dark register">Sign up</router-link>
        </div>
      </div>
    </div>
  </nav>
</template>


<script setup>
import { useUserStore } from '../store/user'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.logo-img {
  width: 2.8125rem;
  height: 2.8125rem;
}

span {
  color: rgba(255, 255, 255, 1);
  margin: 0.3125rem 1.875rem 0 0.1875rem;
}

.links {
  color: rgb(179, 137, 110);
  text-decoration: none;
  font-size: 1.375rem;
  margin-right: 1.25rem;
  border: 1px solid transparent;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.login,
.register {
  font-size: 1.375rem;
  border-radius: 0.3125rem;
  white-space: nowrap;
  min-width: 6.875rem;
  transition: background-color 0.3s ease, border 0.3s ease, color 0.3s ease;
}

.login {
  border: 1px solid rgb(179, 137, 110);
  color: rgb(179, 137, 110);
}

.login:hover,
.links:hover {
  background-color: rgb(179, 137, 110);
  border-color: rgb(133, 102, 82);
  color: rgba(255, 255, 255, 1);
}

.register {
  background-color: rgb(179, 137, 110);
  border: 1px solid rgb(179, 137, 110);
}

.register:hover {
  background-color: rgb(133, 102, 82);
  border-color: rgb(133, 102, 82);
  color: rgba(0, 0, 0, 1);
}

/* Responsive */
@media (max-width: 991.98px) {
  .logo-img {
    width: 2.1875rem;
    height: 2.1875rem;
  }

  .navbar-collapse {
    height: 30rem;
    overflow: hidden;
  }

  .navbar-brand span {
    font-size: 1.5rem;
  }

  .links,
  .login,
  .register {
    font-size: 1rem;
  }

  .logo {
    margin: 0.5rem 0 0 0;
  }

  .navbar-nav,
  .navbar-collapse,
  .links-right {
    width: 100%;
    text-align: center;
  }

  .links-right {
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    margin: 12rem 0 0 0;
  }

  .login,
  .register {
    width: 100%;
  }

  .navbar-brand {
    margin-bottom: 1rem;
  }

  .navbar-toggler {
    border: none;
  }

  .navbar-toggler:focus {
    box-shadow: none;
    outline: none;
  }

  .navbar-toggler-icon {
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 30'%3e%3cpath stroke='rgba(179, 137, 110, 1)' stroke-linecap='round' stroke-miterlimit='10' stroke-width='2' d='M4 7h22M4 15h22M4 23h22'/%3e%3c/svg%3e");
    width: 1.3em;
    height: 1.3em;
    margin: 0;
  }
}
</style>