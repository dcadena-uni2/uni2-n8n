// <ui-estandar> Interfaz estándar de los formularios n8n de UNI2 (issue #389).
// Fuente única: n8n_ui/ui_estandar.js. Los scripts build_*.py la copian en el nodo "UI estándar"
// de cada flujo: no editar a mano dentro de n8n.
// Patrones de marca tomados de Reconstruye y del Extractor: naranja UNI2, Nunito, barra con el logo
// de Finamiga, tarjeta centrada, botones redondeados y pantalla "Procesando…".
// Seguridad: todo texto dinámico pasa por esc(); los formularios llevan el campo oculto de sesión.

const UI_ESTILOS = `<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--naranja:#f08a24;--naranja-osc:#d97316;--naranja-suave:rgba(240,138,36,.14);--texto:#3b3b3b;--texto-suave:#6e6e6e;--borde:#cfd2d6;--linea:#ececec;--fondo:#f4f5f7;--blanco:#fff;--error:#e5484d;--exito:#2f9e62;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{-webkit-text-size-adjust:100%;}
body{min-height:100vh;display:flex;flex-direction:column;background:var(--fondo);font-family:'Nunito','Open Sans',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:15px;color:var(--texto);}
.env-banner{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:4px 12px;padding:10px 16px;background:var(--naranja);color:#1f1f1f;font-size:13px;font-weight:800;letter-spacing:.4px;text-align:center;}
.env-banner .sep{opacity:.55;}
.env-banner .usuario{font-weight:700;}
.env-banner a{color:inherit;font-weight:700;text-decoration:underline;text-underline-offset:2px;}
.navbar{background:var(--blanco);box-shadow:0 1px 6px rgba(0,0,0,.07);padding:14px 16px;display:flex;justify-content:center;}
.navbar img{height:44px;display:block;}
.container{width:100%;max-width:480px;margin:auto;padding:32px 16px;}
.container.ancho{max-width:760px;}
.card{background:var(--blanco);border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.06);padding:32px 28px;}
.card h1{font-size:22px;font-weight:700;color:var(--texto);text-align:center;margin-bottom:6px;}
.card p{color:var(--texto-suave);line-height:1.6;text-align:center;}
.card p.descripcion{margin-bottom:6px;}
form{display:flex;flex-direction:column;}
label{align-self:flex-start;position:relative;z-index:1;top:9px;margin:14px 0 0 12px;padding:0 6px;background:var(--blanco);font-size:13px;font-weight:600;color:var(--texto-suave);}
input,select,textarea{width:100%;height:50px;border:1px solid var(--borde);border-radius:6px;padding:0 14px;font:inherit;color:var(--texto);background-color:var(--blanco);transition:border-color .15s,box-shadow .15s;}
textarea{height:110px;padding:14px;resize:vertical;}
input[type=file]{height:auto;padding:12px 14px;}
select{appearance:none;-webkit-appearance:none;padding-right:42px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%236e6e6e' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 16px center;}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--naranja);box-shadow:0 0 0 3px var(--naranja-suave);}
.hint{font-size:12px;color:var(--texto-suave);margin:6px 2px 0;text-align:left!important;}
button{margin-top:28px;height:48px;border:none;border-radius:24px;background:var(--naranja);color:#fff;font:inherit;font-size:15px;font-weight:800;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:background .15s,transform .05s;}
button:hover{background:var(--naranja-osc);}
button:active{transform:translateY(1px);}
button:disabled{opacity:.65;cursor:not-allowed;}
.btn{display:block;margin-top:24px;height:48px;line-height:48px;border-radius:24px;background:var(--naranja);color:#fff;text-align:center;text-decoration:none;font-size:14px;font-weight:800;letter-spacing:1px;text-transform:uppercase;transition:background .15s;}
.btn:hover{background:var(--naranja-osc);}
.btn-back{display:block;margin-top:12px;height:48px;line-height:46px;border:1.5px solid var(--naranja);border-radius:24px;color:var(--naranja);background:transparent;text-align:center;text-decoration:none;font-size:14px;font-weight:800;letter-spacing:1px;text-transform:uppercase;transition:background .15s;}
.btn-back:hover{background:var(--naranja-suave);}
.status-icon{width:60px;height:60px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 18px;font-size:28px;color:#fff;}
.status-icon.exito{background:var(--exito);}
.status-icon.error{background:var(--error);}
.status-icon.aviso{background:var(--naranja);}
.mensaje{background:var(--fondo);border-radius:8px;padding:14px 16px;margin-top:16px;font-size:14px;line-height:1.7;text-align:left!important;word-break:break-word;color:var(--texto)!important;}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,.45);border-top-color:#fff;border-radius:50%;animation:girar .8s linear infinite;vertical-align:-3px;margin-right:8px;}
@keyframes girar{to{transform:rotate(360deg);} }
.overlay{position:fixed;inset:0;background:rgba(244,245,247,.82);display:none;flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:100;font-weight:700;color:var(--texto);}
.overlay.show{display:flex;}
.overlay .spinner{width:38px;height:38px;border-width:3px;border-color:var(--naranja-suave);border-top-color:var(--naranja);margin:0;}
.alerta{border-radius:8px;padding:12px 14px;margin:16px 0 4px;font-size:14px;line-height:1.5;text-align:left;}
.alerta.error{background:rgba(229,72,77,.10);border:1px solid rgba(229,72,77,.35);color:#b42318;}
.res-contadores{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0 12px;}
.chip{border-radius:10px;padding:12px 8px;text-align:center;font-size:13px;font-weight:700;color:var(--texto-suave);background:var(--fondo);border:1px solid var(--linea);}
.chip b{display:block;font-size:24px;line-height:1.1;font-weight:800;}
.chip.ok b{color:var(--exito);}.chip.mal b{color:var(--error);}.chip.neutro b{color:var(--texto-suave);}
.chip.ok.activo{background:rgba(47,158,98,.08);border-color:rgba(47,158,98,.35);}
.chip.mal.activo{background:rgba(229,72,77,.08);border-color:rgba(229,72,77,.35);}
.res-integracion{border-radius:8px;padding:10px 14px;font-size:14px;text-align:center;margin-bottom:6px;}
.res-integracion.ok{background:rgba(47,158,98,.10);color:#1e7a4a;}
.res-integracion.mal{background:rgba(229,72,77,.10);color:#b42318;}
.res-seccion{margin-top:16px;border:1px solid var(--linea);border-left:4px solid var(--borde);border-radius:8px;padding:12px 14px;text-align:left;}
.res-seccion.ok{border-left-color:var(--exito);}.res-seccion.mal{border-left-color:var(--error);}.res-seccion.neutro{border-left-color:#9aa0a6;}
.res-seccion h3{font-size:14px;font-weight:800;color:var(--texto);margin-bottom:6px;display:flex;align-items:center;gap:8px;}
.res-seccion .cuenta{background:var(--fondo);border-radius:10px;padding:1px 8px;font-size:12px;color:var(--texto-suave);}
.res-seccion ul{list-style:none;}
.res-seccion li{padding:8px 0;border-top:1px solid var(--linea);font-size:14px;line-height:1.5;word-break:break-word;}
.res-seccion li:first-child{border-top:none;}
.res-seccion li strong{display:block;font-weight:700;color:var(--texto);}
.res-seccion li span{display:block;color:var(--texto-suave);}
.res-seccion li strong .nit{display:inline;font-weight:600;color:var(--texto-suave);font-size:13px;}
@media (max-width:600px){.res-contadores{gap:6px;}.chip{padding:10px 4px;font-size:12px;}.chip b{font-size:20px;}}
.card ul.consejos{list-style:none;margin-top:12px;color:var(--texto-suave);line-height:1.6;text-align:center;}
.card .detalle-tecnico{margin-top:14px;font-size:12px;color:#9a9a9a;word-break:break-word;}
@media (max-width:600px){.navbar img{height:36px;}.container{padding:20px 12px;}.card{padding:24px 18px;border-radius:10px;}.card h1{font-size:19px;}.env-banner{font-size:12px;}.env-banner .sep{display:none;}}
</style>`;

const UI_LOGO = 'https://qa-app.uni2.com.co/static/media/finamiga-logo.e0b055b68356be94cbe4.svg';

// Muestra "Procesando…" al enviar un formulario o seguir un botón, y evita el doble envío.
const UI_SCRIPT = `<div class="overlay" id="cargando"><span class="spinner"></span><span>Procesando, por favor espera...</span></div><script>(function(){var ov=document.getElementById("cargando");function mostrar(btn){if(btn){btn.disabled=true;btn.setAttribute("data-txt",btn.textContent);btn.textContent=" Procesando...";var sp=document.createElement("span");sp.className="spinner";btn.insertBefore(sp,btn.firstChild);} ov.classList.add("show");} function restaurar(){ov.classList.remove("show");document.querySelectorAll("form").forEach(function(f){f.removeAttribute("data-enviando");var b=f.querySelector("button");if(b&&b.getAttribute("data-txt")){b.disabled=false;b.textContent=b.getAttribute("data-txt");} });} document.querySelectorAll("form").forEach(function(f){f.addEventListener("submit",function(e){if(f.getAttribute("data-enviando")){e.preventDefault();return;} f.setAttribute("data-enviando","1");mostrar(f.querySelector("button"));});});document.querySelectorAll("a.btn,a.btn-back").forEach(function(a){a.addEventListener("click",function(){mostrar(null);});});window.addEventListener("pageshow",function(e){if(e.persisted){restaurar();} });})();</script>`;

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Banner con el nombre de la aplicación, el usuario autenticado y "Cerrar sesión"
function uiBanner(app, usuario, urlSalir) {
  return '<div class="env-banner"><span>' + esc(app) + '</span>'
    + (usuario ? '<span class="sep">|</span><span class="usuario">' + esc(usuario) + '</span>' : '')
    + (urlSalir ? '<a href="' + esc(urlSalir) + '">Cerrar sesión</a>' : '') + '</div>';
}

// Partes fijas de la página: inicio (hasta abrir la tarjeta) y fin (cierre + "Procesando…")
function uiMarco({ titulo, app, usuario, urlSalir, ancho = false }) {
  return {
    inicio: '<!doctype html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
      + '<title>' + esc(titulo) + '</title>' + UI_ESTILOS + '</head><body>' + uiBanner(app, usuario, urlSalir)
      + '<div class="navbar"><img src="' + UI_LOGO + '" alt="Finamiga"></div><div class="container' + (ancho ? ' ancho' : '') + '"><div class="card">',
    fin: '</div></div>' + UI_SCRIPT + '</body></html>',
  };
}

// Formulario a partir de una lista de campos.
// campo: { nombre, etiqueta, tipo: 'text'|'number'|'password'|'email'|'date'|'select'|'textarea'|'file',
//          requerido, opciones: [texto | {valor, texto}], valor, placeholder, ayuda, aceptar (tipos de archivo),
//          patron (regex HTML, p. ej. '\\d{8}'), mensajePatron, longitud (máx. caracteres), teclado ('numeric'…) }
// error: mensaje que se muestra arriba del formulario (p. ej. validación del servidor).
// La validación del navegador (patron) es solo ayuda: el flujo siempre debe validar de nuevo.
function uiFormulario({ titulo, descripcion, accion, campos, boton = 'Enviar', campoSesion = '', error = '' }) {
  const conArchivo = campos.some((c) => c.tipo === 'file');
  let html = '<h1>' + esc(titulo) + '</h1>' + (descripcion ? '<p class="descripcion">' + esc(descripcion) + '</p>' : '')
    + (error ? '<div class="alerta error">' + esc(error) + '</div>' : '')
    + '<form method="POST" action="' + esc(accion) + '"' + (conArchivo ? ' enctype="multipart/form-data"' : '') + '>' + campoSesion;
  for (const c of campos) {
    const id = 'f_' + String(c.nombre).replace(/[^A-Za-z0-9_]/g, '_');
    const req = c.requerido ? ' required' : '';
    html += '<label for="' + id + '">' + esc(c.etiqueta) + '</label>';
    if (c.tipo === 'select') {
      html += '<select name="' + esc(c.nombre) + '" id="' + id + '"' + req + '>';
      for (const o of c.opciones || []) {
        const valor = typeof o === 'object' ? o.valor : o;
        const texto = typeof o === 'object' ? o.texto : o;
        html += '<option value="' + esc(valor) + '"' + (String(valor) === String(c.valor ?? '') ? ' selected' : '') + '>' + esc(texto) + '</option>';
      }
      html += '</select>';
    } else if (c.tipo === 'textarea') {
      html += '<textarea name="' + esc(c.nombre) + '" id="' + id + '"' + req + (c.placeholder ? ' placeholder="' + esc(c.placeholder) + '"' : '') + '>' + esc(c.valor ?? '') + '</textarea>';
    } else {
      html += '<input type="' + esc(c.tipo || 'text') + '" name="' + esc(c.nombre) + '" id="' + id + '"' + req
        + (c.valor != null && c.tipo !== 'file' && c.tipo !== 'password' ? ' value="' + esc(c.valor) + '"' : '')
        + (c.placeholder ? ' placeholder="' + esc(c.placeholder) + '"' : '')
        + (c.patron ? ' pattern="' + esc(c.patron) + '"' : '')
        + (c.mensajePatron ? ' title="' + esc(c.mensajePatron) + '"' : '')
        + (c.longitud ? ' maxlength="' + Number(c.longitud) + '"' : '')
        + (c.teclado ? ' inputmode="' + esc(c.teclado) + '"' : '')
        + (c.aceptar ? ' accept="' + esc(c.aceptar) + '"' : '') + ' autocomplete="off">';
    }
    if (c.ayuda) html += '<p class="hint">' + esc(c.ayuda) + '</p>';
  }
  return html + '<button type="submit">' + esc(boton) + '</button></form>';
}
// </ui-estandar>
