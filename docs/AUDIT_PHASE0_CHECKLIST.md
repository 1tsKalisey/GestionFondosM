# Fase 0 - Estabilizacion Base

## Objetivo

Estabilizar la base del proyecto antes de corregir los hallazgos `P0` detectados en la auditoria funcional y tecnica.

## Freeze Temporal

Hasta cerrar los `P0`, no se deben introducir cambios nuevos de funcionalidad en estas areas:

- `categories`
- `budgets`
- `reports`
- `sync`

Reglas de actuacion durante este freeze:

- Solo se permiten cambios de correccion directamente relacionados con los `P0`.
- No se aceptan refactors cosmeticos ni ampliaciones de alcance en los modulos congelados.
- Cualquier cambio en UI dentro de estas areas debe estar justificado por una correccion `P0`.
- Antes de mezclar cambios, validar manualmente la checklist de esta fase.

## Rama de Trabajo

Rama de correccion creada para esta fase:

- `fix/audit-p0-stabilization`

## Checklist Manual Minima

Ejecutar esta checklist despues de cada bloque de correccion `P0` y antes de dar por estable la base.

### 1. Login

- Abrir la app y verificar que la pantalla de login carga sin errores visuales.
- Iniciar sesion con credenciales validas.
- Confirmar que la navegacion posterior al login lleva a una pantalla operativa.
- Verificar que no aparece error de sesion ni cierre inesperado.

### 2. Crear transaccion

- Entrar en alta de transaccion desde el flujo normal.
- Crear un gasto valido.
- Crear un ingreso valido.
- Confirmar que ambos quedan visibles en las vistas dependientes.
- Verificar que no aparece error de guardado ni bloqueo de pantalla.

### 3. Crear categoria

- Entrar en `Categorias`.
- Crear una categoria nueva con un grupo existente.
- Crear una categoria nueva con grupo personalizado, si aplica.
- Confirmar que la categoria aparece en el catalogo.
- Verificar que luego puede seleccionarse desde otros flujos que dependan de categorias.

### 4. Crear y editar presupuesto

- Entrar en `Presupuestos`.
- Crear un presupuesto valido para el mes activo.
- Editar un presupuesto ya existente.
- Confirmar que la lista mensual refleja el alta y la edicion.
- Verificar que no hay errores al volver a entrar en la pantalla.

### 5. Ver reportes

- Entrar en `Reportes`.
- Cambiar el rango de fechas.
- Confirmar que la pantalla recalcula sin error.
- Verificar que los datos mostrados son coherentes con las transacciones del rango.

### 6. Sync manual

- Entrar en `Estado de sincronizacion`.
- Lanzar `Sincronizar ahora`.
- Confirmar que la app no se bloquea.
- Verificar que se actualizan estado, errores y cambios pendientes.

### 7. Quick entry

- Abrir `Quick entry`.
- Registrar un importe positivo.
- Registrar un importe negativo.
- Confirmar que ambos movimientos se guardan sin error.
- Verificar que el flujo permite volver a `Dashboard`.
