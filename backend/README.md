## Backend – AI Copilot API

This is the backend of the AI Copilot project, built with **NestJS**, **TypeORM**, **JWT authentication**, and **OpenAI API integration**.

### 🚀 Getting Started

```bash
cd backend
npm install
npm run start:dev
```
### 🛠 Requirements

- Node.js (v18+ recommended)  
- PostgreSQL or SQLite (for development)  
- `.env` file (see below)  


### 🔐 Environment Variables

Create a `.env` file in the `backend/` folder:

```env
JWT_SECRET=your-jwt-secret
DB_HOST=localhost
DB_PORT=5432
DB_USER=youruser
DB_PASSWORD=yourpassword
DB_NAME=ai_copilot
OPENAI_API_KEY=your-openai-key
```
### 🗂️ Project Structure

- `src/auth/` – Authentication (login/register, JWT)  
- `src/user/` – User management  
- `src/ai/` – OpenAI integration (planned)  
- `src/common/` – Shared utilities and guards  
- `src/main.ts` – Application entry point  

### ✅ Features (Planned)

- User registration and login (JWT-based)  
- Document upload and processing  
- OpenAI embedding generation  
- RAG-based question answering  
- Real-time communication (WebSocket)

