import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import './app/global.css';
import './app/editorial.css';
import './app/motion.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
