// main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { CssBaseline } from "@mui/material";

// Global stiller ve/veya tema eklemeleri yapabilirsiniz
import "./index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    {/* CssBaseline, Material UI'nın global reset stilini uygular */}
    <CssBaseline />
    <App />
  </React.StrictMode>
);
