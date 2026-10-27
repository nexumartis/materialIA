# Aceptación en navegador — chat público

`chat-publico.mjs` maneja Chrome con `playwright-core` (dependencia dev exacta). Comprueba:

- privacidad entre compradores (S1);
- recuperación tras recargar, pagar o cambiar de tienda (S2 y S3);
- respuestas tardías al reiniciar o cambiar de tienda (S4 a S6);
- referencias inválidas (S7);
- chat demo (S8);
- tokens fuera de URLs y consola (S9);
- ancho de 390 px (S10).

**Sólo opera sobre servicios locales.** Aborta si la API o la web no están en loopback, o si `/health` no informa `APP_ENV=local`, pagos `simulated` y LLM `mock`. Usa las tiendas sintéticas del seed (`sanitarios-demo-c`, `ferreteria-demo-d`). Cada corrida compra y paga en el checkout simulado una unidad del flexible del seed C (hay 40). `supabase db reset` lo restaura.

## Correr

1. Base local con migraciones 0001–0006 y seed (`supabase db reset`, o un Postgres de prueba equivalente).
2. Backend, con `DATABASE_URL` apuntando a esa base y sin claves reales:

   ```bash
   cd backend
   APP_ENV=local PAYMENT_PROVIDER=simulated LLM_PROVIDER=mock uvicorn app.main:app --host 127.0.0.1 --port 8077
   ```
3. Frontend, desde `web/`:

   ```bash
   npm ci
   npm run build
   npm run preview -- --host 127.0.0.1 --strictPort   # http://127.0.0.1:4173
   ```
4. Aceptación, desde `web/`: `npm run e2e`. Termina con código 0 si todo pasa y 1 si algo falla. Para conservar la salida: `npm run e2e > ruta/fuera/del/repo.log`.

## Variables opcionales

| Variable | Default |
|---|---|
| `E2E_API` | `http://127.0.0.1:8077` (debe coincidir con `VITE_API_BASE` del build) |
| `E2E_WEB` | `http://127.0.0.1:4173` |
| `E2E_CHROME_CHANNEL` | `chrome` (Chrome instalado; `msedge` también sirve) |
| `E2E_CHROME_PATH` | ejecutable de Chromium/Chrome; reemplaza al canal |
| `E2E_HEADED` | `1` para ver el navegador |

`playwright-core` no descarga navegadores. Para usar uno propio de Playwright: `npx playwright-core install chromium` y apuntá `E2E_CHROME_PATH` a ese ejecutable.
