<template>
    <header class="app-navbar">
      <div class="app-navbar-inner">
        <!-- Left -->
        <div class="app-navbar-left">
          <div class="app-navbar-brand">
            <img src="/img/ai-logo.svg" alt="AIVA Logo" class="app-navbar-logo" />
            <span class="app-navbar-title">AIVA</span>
          </div>
  
          <div v-if="showSearch" class="app-navbar-search">
            <div class="input-group search-wrapper">
              <span class="input-group-text bg-white border-end-0">
                <i class="bi bi-search text-muted"></i>
              </span>
              <input
                :value="searchValue"
                type="text"
                class="form-control border-start-0 search-input"
                :placeholder="searchPlaceholder"
                @input="onSearchInput"
              />
            </div>
          </div>
        </div>
  
        <!-- Right -->
        <div class="app-navbar-right">
          <button
            v-if="showShare"
            type="button"
            class="btn btn-share px-3 py-2"
            @click="$emit('share')"
          >
            <i class="bi bi-share me-1"></i> Share
          </button>
  
          <button
            v-if="showUpgrade"
            type="button"
            class="btn btn-upgrade px-3 py-2"
            @click="$emit('upgrade')"
          >
            <i class="bi bi-stars me-1"></i> Upgrade
          </button>
  
          <button
            v-if="showUser"
            type="button"
            class="btn btn-user px-3 py-2 d-flex align-items-center gap-2"
            @click="$emit('user-click')"
          >
            <span class="fw-semibold user-name">{{ userName }}</span>
            <i class="bi bi-chevron-down small"></i>
          </button>
        </div>
      </div>
    </header>
  </template>
  
  <script setup lang="ts">
  const props = withDefaults(defineProps<{
    userName?: string
    showSearch?: boolean
    showShare?: boolean
    showUpgrade?: boolean
    showUser?: boolean
    searchPlaceholder?: string
    searchValue?: string
  }>(), {
    userName: '',
    showSearch: true,
    showShare: false,
    showUpgrade: false,
    showUser: true,
    searchPlaceholder: 'Search',
    searchValue: '',
  })
  
  const emit = defineEmits<{
    (e: 'update:searchValue', value: string): void
    (e: 'share'): void
    (e: 'upgrade'): void
    (e: 'user-click'): void
  }>()
  
  const onSearchInput = (event: Event) => {
    const target = event.target as HTMLInputElement
    emit('update:searchValue', target.value)
  }
  </script>
  
  <style scoped>
  .app-navbar {
    width: 100%;
    border-bottom: 1px solid rgb(236 231 227);
    padding: 1rem 1.5rem;
  }
  
  .app-navbar-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.25rem;
  }
  
  .app-navbar-left {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    min-width: 0;
    flex: 1;
  }
  
  .app-navbar-brand {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    flex-shrink: 0;
  }
  
  .app-navbar-logo {
    height: 2.5rem; 
    filter: invert(61%) sepia(39%) saturate(532%) hue-rotate(339deg) brightness(90%) contrast(85%); 
  }
  
  .app-navbar-title {
    font-size: 2rem;
    font-weight: 700;
    color: rgb(179, 137, 110);
    line-height: 1;
  }
  
  .app-navbar-search {
    width: 100%;
    max-width: 45rem;
  }
  
  .search-wrapper {
    border-radius: 0.75rem;
    overflow: hidden;
  }
  
  .search-input {
    box-shadow: none;
  }
  
  .search-input:focus {
    box-shadow: none;
    border-color: rgb(222 226 230);
  }
  
  .app-navbar-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }
  
  .btn-share {
    background: white;
    border: 1px solid rgb(227 221 217);
    border-radius: 0.75rem;
    color: rgb(113, 85, 69);
  }
  
  .btn-share:hover {
    background: rgb(247 244 242);
    border-color: rgb(215 205 198);
  }
  
  .btn-upgrade {
    background: rgb(247 237 232);
    border: 1px solid rgb(231 207 194);
    border-radius: 0.75rem;
    color: rgb(113, 85, 69);
  }
  
  .btn-upgrade:hover {
    background: rgb(242 227 219);
    border-color: rgb(220 193 179);
  }
  
  .btn-user {
    background: rgb(247 237 232);
    border: 1px solid rgb(231 207 194);
    border-radius: 0.75rem;
    color: rgb(113, 85, 69);
  }
  
  .btn-user:hover {
    background: rgb(242 227 219);
    border-color: rgb(220 193 179);
  }
  
  .user-name {
    color: rgb(113, 85, 69);
  }
  
  @media (max-width: 992px) {
    .app-navbar-inner {
      flex-direction: column;
      align-items: stretch;
    }
  
    .app-navbar-left,
    .app-navbar-right {
      width: 100%;
    }
  
    .app-navbar-logo {
      flex-direction: column;
      align-items: stretch;
      gap: 1rem;
    }
  
    .app-navbar-brand {
      align-self: flex-start;
    }
  
    .app-navbar-right {
      justify-content: flex-end;
      flex-wrap: wrap;
    }
  
    .app-navbar-search {
      max-width: 100%;
    }
  }
  </style>