import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import IntradayScreener from "../intraday-screener.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <IntradayScreener />
  </StrictMode>
);
