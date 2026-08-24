# RepoIR Frontend: The Semantic Interface

The official React-based dashboard for the RepoIR search engine. This interface provides a beautiful, responsive, and intuitive way to manage your private data vault and perform semantic searches.

---

## ✨ Features

- **Omni-Search Bar**: Perform natural language queries across all your documents, images, and web links.
- **Visual Analytics**: Real-time charts showing your data distribution across different categories.
- **Activity Timeline**: Track your ingestion history and search patterns in a sleek sidebar.
- **Cloud Vault Manager**: Securely connect and unlock your Google Drive vault with password-protected AES session syncing.
- **Multimodal Ingestor**: 
  - Drag-and-drop file uploads.
  - One-click URL scanning.
  - Rapid text snippet indexing.
- **Smart Previews**: View your cloud-stored documents and images directly within the app via secure streaming proxies.

---

## 🛠️ Technical Implementation

### Frontend Stack
- **Framework**: [React 18+](https://reactjs.org/) with [Vite](https://vitejs.dev/) for ultra-fast HMR.
- **Language**: [TypeScript](https://www.typescriptlang.org/) for robust type-safety.
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/) for a premium, modern aesthetic.
- **State Management**: React Context API for authentication and global application state.

### Backend Connectivity
The frontend communicates with the FastAPI backend via a dedicated `api.ts` layer that handles:
- **JWT Authorization**: Automatic token attachment to requests.
- **Job Polling**: Real-time status updates for heavy ingestion tasks.
- **Error Handling**: Graceful fallback UI for network or auth issues.

---

## 📥 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) (v18 or higher)
- [npm](https://www.npmjs.com/) or [bun](https://bun.sh/)

### Installation
```bash
# Navigate to the frontend directory
cd "RepoIR Frontend"

# Install dependencies
npm install

# Configure environment (Optional)
# Create .env.local and set VITE_API_BASE_URL if running a local backend
# echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

# Launch the development server
npm run dev
```
The app will be available at `http://localhost:5173`.

---

## 📁 Project Structure

| Directory | Purpose |
| :--- | :--- |
| `src/components` | UI primitives and feature-specific React components. |
| `src/contexts` | Global state (Auth, App Settings). |
| `src/pages` | Route definitions (Search, Dashboard, Auth). |
| `src/lib` | API wrappers (`api.ts`) and utility functions. |
| `src/hooks` | Custom React hooks for API polling and UI logic. |

---

## 📄 License
This project is proprietary. All rights reserved.
