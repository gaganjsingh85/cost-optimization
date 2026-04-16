import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App';

// NOTE: React.StrictMode removed to prevent intentional double-mount in dev,
// which was firing every API call twice. The API client also has in-flight
// request dedup as a second line of defense.
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);