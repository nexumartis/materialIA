# Probar WhatsApp con el número de prueba de Meta

Etapa 1: el agente recibe y contesta texto. Diseño en
[superpowers/specs/2026-11-08-whatsapp-design.md](superpowers/specs/2026-11-08-whatsapp-design.md).

**Antes de empezar:** la cuenta de WhatsApp de la app tiene que poder mandar mensajes. El 08/11/2026
Meta respondía el error `131031` («Business account locked») y hay que resolverlo primero.

## Lo que hace falta

- La app de Meta **NexumArtis** con el caso de uso de WhatsApp y el número de prueba
  (`+1 555 165 4354`, Phone Number ID `1389172324285219`, WABA `2571440663368022`).
- Tu celular agregado como destinatario en **Casos de uso → WhatsApp → Paso 1. Pruébalo**.
- Postgres local con todas las migraciones, incluida `0034_whatsapp.sql`.
- `cloudflared`, para que Meta llegue a tu PC por HTTPS. En Windows: `winget install Cloudflare.cloudflared`.

## Paso a paso

1. **Claves en `backend/.env`.** Nunca se suben a GitHub ni se pegan en un chat.
   - `WHATSAPP_APP_SECRET`: app de Meta → Configuración de la app → Básica → Clave secreta.
   - `WHATSAPP_VERIFY_TOKEN`: una frase cualquiera inventada por ustedes. Se usa también en el paso 4.
   - `WHATSAPP_TOKEN_KEY`: generala con
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. **Levantar la API y el worker**, desde `backend/`:
   `uvicorn app.main:app --port 8077` y, en otra terminal, `python -m app.worker`.
3. **Abrir el túnel:** `cloudflared tunnel --url http://127.0.0.1:8077`. Imprime una dirección
   `https://….trycloudflare.com` que cambia cada vez que lo abrís.
4. **Avisarle a Meta adónde mandar los mensajes.** En la app de Meta, en WhatsApp → Configuración:
   - URL de devolución de llamada: `https://<la dirección del túnel>/channels/whatsapp/webhook`.
   - Token de verificación: el mismo `WHATSAPP_VERIFY_TOKEN`.
   - Verificar y guardar. Después, en «Campos del webhook», suscribirse a `messages`.
5. **Conectar el número de prueba al negocio de demo C.** Generá un token en **Paso 1. Pruébalo**
   (dura 24 horas). En PowerShell, desde `backend/`:

   ```powershell
   $env:WHATSAPP_CONNECT_TOKEN = "<token generado>"
   python -m app.whatsapp connect --tenant 0000000c-0000-0000-0000-00000000000c --phone-number-id 1389172324285219 --waba-id 2571440663368022 --display-phone "+1 555 165 4354"
   Remove-Item Env:WHATSAPP_CONNECT_TOKEN
   ```

   Cuando el token vence, se repite este paso con uno nuevo.
6. **Probar.** Desde tu celular, escribile al `+1 555 165 4354`: «hola, tienen canillas?».

## Qué tiene que pasar

- Te llega la respuesta del agente con productos del catálogo del negocio C.
- En el panel del negocio C, la conversación aparece en **Conversaciones** con tu mensaje y la respuesta.
- Si respondés desde la bandeja del panel, el mensaje te llega por WhatsApp.

## Si no llega

- En la app de Meta, **Paso 1. Pruébalo → Revisa los webhooks de prueba** muestra lo que mandó Meta
  y los errores de envío (por ejemplo, `131031`).
- La tabla `whatsapp_outbox` guarda cada envío con `status` (`pending`, `sent`, `failed`,
  `window_closed`) y `last_error`.
- `window_closed`: pasaron más de 24 horas desde tu último mensaje. Escribí de nuevo.
