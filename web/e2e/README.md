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

# Aceptación en navegador — comprobantes y constancia

`comprobantes.mjs` recorre el flujo completo:

1. El comprador arma un pedido y adjunta un comprobante sintético dibujado en el navegador. Queda recibido, el worker lo lee y el pedido **no** se marca pagado.
2. El dueño inicia sesión y ve el comprobante leído. Confirma la transferencia con doble clic: el pedido queda pagado y el comprobante, asociado.
3. El comprador recarga y ve **una** constancia, que descarga en PDF. Sin token, no se abren ni su conversación ni la constancia.
4. El dueño descarga el registro del mes en CSV.
5. Sin desborde horizontal a 390 px, ni para el comprador ni para el dueño.
6. Sin tokens del comprador en las URLs.

Mismas salvaguardas que `chat-publico.mjs`: sólo loopback, `APP_ENV=local`, pagos `simulated` y LLM `mock`. Cada corrida usa una referencia bancaria y un archivo únicos, y consume una unidad del flexible del seed C.

Además necesita:

- **El worker corriendo** contra la misma base, para leer el comprobante: `WORKER_INTERVAL_S=2 python -m app.worker`.
- **Un dueño de la tienda C** que pueda iniciar sesión en el Supabase Auth local y tenga su membresía en la base de la API. Pasale las credenciales por variables; no van en el repo:

```bash
E2E_OWNER_EMAIL=… E2E_OWNER_PASSWORD=… npm run e2e:comprobantes
```

# Aceptación en navegador — bandeja y toma de control

`bandeja.mjs` (`npm run e2e:bandeja`) recorre el flujo:

1. El cliente pide una persona.
2. El dueño la ve en «Derivadas» y toma el control.
3. El cliente escribe: el asistente **no** responde y aparece «Te está atendiendo una persona del negocio».
4. El dueño responde y el cliente lo ve como «Equipo de <negocio>».
5. El dueño la devuelve y el asistente vuelve a responder.
6. Sin desborde horizontal a 390 px, ni para el cliente ni para el dueño.

Mismas salvaguardas y variables (`E2E_OWNER_EMAIL`, `E2E_OWNER_PASSWORD`) que `comprobantes.mjs`. No necesita el worker.

**Al terminar, frená el worker y la API de prueba** (`pkill -f app.worker`). Un worker que queda corriendo contra la base de pytest compite con los tests.

# Aceptación en navegador — asistente paso a paso

`asistente.mjs` (`npm run e2e:asistente`) recorre el flujo:

1. El asistente muestra los 8 pasos y marca el catálogo como listo.
2. El dueño cambia el saludo; el borrador sobrevive a una recarga.
3. La vista previa responde con el borrador mientras la tienda sigue sin cambios.
4. Al publicar (o «Publicar igual» si fallan pruebas del negocio), la tienda pública saluda con lo nuevo.
5. Sin desborde horizontal a 390 px.

Mismas salvaguardas y variables que `bandeja.mjs`. **Publica el perfil de la tienda C en la base de prueba.** El registro no se recorre: en el entorno aislado, el Auth local y la base de la API son distintos.
