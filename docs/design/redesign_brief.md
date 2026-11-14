# AstroHealth — rediseño integral para Claude Code

## Encargo del usuario y prioridad

Actúa como diseñador senior de producto, especialista en HCI y desarrollador frontend. Trabajas en Claude Code dentro de VS Code, con el modelo que el usuario haya seleccionado. Tu tarea es **reinventar por completo la interfaz de AstroHealth e implementarla en React**.

**El usuario rechazó expresamente el diseño anterior.** La composición, la barra lateral, los paneles, las ilustraciones orbitales, la tipografía y los acentos turquesa existentes no son referencias que debas conservar. La preferencia anterior de contenido claro con barra oscura quedó sustituida por este encargo. Usa tu criterio para proponer una dirección visual nueva, coherente y reconociblemente diferente; tienes libertad para cambiar organización, componentes, jerarquía, navegación y apariencia.

Conserva los acuerdos de datos y comportamiento que permiten integrar el trabajo de Jorge, Jhonatan e Ismael. La base técnica existente sirve como infraestructura, no como dirección de arte.

## 1. Ubicación y lectura inicial

Repositorio: https://github.com/Almejandro04/TorresTech-AstroHealth

- `main` contiene el contrato aprobado v0.1.0, integrado mediante PR #23.
- La rama `feature/frontend-01-setup`, asociada al PR #24, contiene el frontend inicial. El PR sigue en borrador y su presentación visual fue rechazada.
- Trabaja sobre esa rama para que el rediseño sustituya la propuesta del mismo PR. Antes de cambiar de rama, inspecciona `git status`, remotos y archivos locales. Conserva trabajo ajeno y cambios sin commit; si necesitas aislamiento, prepara un worktree. No uses reset destructivo ni force push.
- Si el checkout no tiene `frontend/`, comprueba la rama antes de generar otro proyecto. Si el estado remoto cambió, usa el estado actual como autoridad y explica cualquier divergencia.

Lee primero:

1. `docs/api_contract.md`.
2. `docs/ux_requirements.md`.
3. `docs/examples/api_examples.json` y `docs/examples/mission_seed.json`.
4. `frontend/package.json`, `frontend/README.md` y la implementación de `src/types/`, `src/services/` y `src/hooks/`.
5. Los issues #2, #10, #11, #12, #13 y #17 para entender la distribución del trabajo.

Si un documento histórico fija la apariencia rechazada, este brief tiene prioridad sobre esa preferencia visual. Los acuerdos funcionales del contrato siguen vigentes.

## 2. Producto que estás diseñando

AstroHealth es el prototipo de TorresTech para el NASA Space Apps Challenge 2026: monitoreo de indicadores de salud durante una misión espacial ficticia. La experiencia debe ayudar a identificar al astronauta, entender observaciones y tendencias, consultar explicaciones y registrar bienestar diario.

La interfaz está en **inglés**. La comunicación con el usuario puede ser en español. Mantén la identidad propia de AstroHealth/TorresTech y una inspiración visual NASA. Los datos de demostración deben identificarse como sintéticos y las interpretaciones como experimentales.

Entrega una experiencia de producto de cuatro secciones, con contenido de demostración útil:

| Sección | Experiencia esperada |
| --- | --- |
| Dashboard | Identidad y día de misión, indicadores con unidades y fecha propia, sueño/ánimo y acceso al contexto relevante |
| Analytics | Series temporales legibles, selección del periodo y comparación con la referencia individual cuando esté disponible |
| Alerts | Niveles de atención, estado, fecha y detalle de la explicación/evidencia; estados de análisis diferenciados |
| Journal | Sueño, ánimo 1–5 y notas; crear/corregir la entrada del día, guardar, cancelar y recuperar errores |

Reemplaza las pantallas genéricas de “View in preparation” por una propuesta revisable y navegable. Implementa las interacciones de presentación con los datos sintéticos y adaptadores mock disponibles. Cuando una operación persistente o del backend aún no exista, delimita claramente el comportamiento de demostración y conserva un punto de integración tipado. No simules que una API real guardó datos.

El rediseño puede adelantar presentación de los futuros issues de frontend; al entregar, distingue qué quedó implementado, qué se demostró con mocks y qué sigue pendiente. No cierres otros issues automáticamente por haber dibujado sus vistas.

## 3. Dirección visual NASA y colores funcionales

Referencia oficial:
https://www.nasa.gov/nasa-brand-center/brand-guidelines/

La guía cromática de la insignia publicada por NASA especifica:

- **NASA Blue: `#0032A0`**, RGB 0, 50, 160.
- **NASA Red: `#E4002B`**, RGB 228, 0, 43.
- Lámina de referencia: https://www.nasa.gov/wp-content/uploads/2023/07/nasa-insignia-colorguide.png

Son referencias de identidad, no una paleta completa de interfaz ni una obligación de pintar todos los controles con esos dos colores. Construye un sistema de diseño propio de AstroHealth: superficies, texto, bordes, acciones, estados, gráficos y foco.

Separa tokens de marca y tokens semánticos, aunque algunos tonos pertenezcan a una familia similar:

| Familia | Uso |
| --- | --- |
| Marca | Identidad, navegación seleccionada y acciones principales; azul NASA como referencia y rojo de marca usado con intención |
| Éxito | Confirmación de acciones como guardar correctamente; verde elegido con contraste suficiente |
| Advertencia | Atención intermedia; ámbar acompañado de etiqueta e icono |
| Error / atención crítica | Errores y atención alta; rojo semántico distinguible por contexto, texto y tratamiento |
| Información | Ayuda, contexto y mensajes informativos; tono propio consistente |
| Desconocido / sin datos | Neutros que comuniquen ausencia o evaluación pendiente |
| Series temporales | Colores distinguibles, leyendas y trazos/símbolos complementarios; no implicar gravedad médica por decoración |

El éxito de un guardado no equivale a un estado de salud normal. Un dato ausente o un análisis pendiente no debe recibir un indicador verde de normalidad. Mantén identificables las acciones primarias frente a las alertas: el rojo de marca no convierte una acción habitual en una alarma.

Define tipografía, escala de espacios, densidad informativa, superficies y estados interactivos. Puedes elegir apariencia clara, oscura o una combinación si justificas su utilidad; el esquema anterior no condiciona esa elección. Prioriza lectura de datos, jerarquía y operaciones frecuentes. Conserva la identidad AstroHealth en lugar de reemplazarla por el logotipo oficial NASA.

## 4. HCI, heurísticas y accesibilidad verificables

Estudia las fuentes indicadas por el usuario:

- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://lawsofux.com/

Aplica feedback de estado, lenguaje reconocible, control del usuario, consistencia, prevención de errores, opciones visibles, eficiencia, jerarquía de contenido, recuperación y ayuda contextual. Usa las leyes pertinentes de Fitts, Hick, Jakob, proximidad y diferenciación visual para justificar decisiones concretas. Documenta brevemente **principio → decisión → comprobación**; citar una lista de principios no demuestra que la interfaz los cumpla.

Criterios del rediseño:

- Diferenciar carga, éxito, fallo, falta de observaciones y análisis pendiente.
- Mantener visibles astronauta, periodo seleccionado, unidad y antigüedad de cada observación.
- Usar labels y ayudas cercanas; no depender del placeholder para identificar un campo.
- Permitir guardar/cancelar el diario, preservar datos ante errores y evitar envíos repetidos durante una operación.
- Mantener navegación predecible, foco visible y operación mediante teclado.
- Complementar color con etiquetas, iconos o trazos; tratar los gráficos también como información accesible.
- Respetar reducción de movimiento y diseñar controles fáciles de señalar y activar.
- Revisar contraste de las parejas reales: al menos 4.5:1 para texto normal, 3:1 para texto grande y 3:1 para los elementos no textuales necesarios para identificar controles/estados, según los criterios aplicables de WCAG.
- Comprobar escritorio y móvil, incluidos 375 px de ancho, sin controles superpuestos ni pérdida de contenido esencial. Comprobar zoom al 200% y una jerarquía legible de encabezados.

Fuentes de contraste:
https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html

## 5. Acuerdos funcionales que se conservan

- Mismos campos, unidades, tipos, endpoints y respuestas del contrato v0.1.0. Si necesitas cambiarlo, presenta primero el motivo y el impacto para aprobación.
- Cada tarjeta usa `summary.latest_metrics`: último valor no nulo del indicador, con su fecha, día, contexto y procedencia originales. Los indicadores pueden pertenecer a instantes distintos.
- En las series históricas se conservan huecos; mostrar un valor previo en una tarjeta no crea una medición nueva.
- Comparaciones por astronauta, unidad y contexto compatibles. No inventar líneas base, umbrales clínicos ni reglas de detección para llenar un diseño.
- `null` significa ausencia; cero no es un sustituto. Usar los estados de análisis del contrato.
- Alertas consultativas con explicación. El motor mantiene `active`/`resolved`; el usuario no las resuelve ni las marca como revisadas en este MVP.
- Diario separado de las mediciones puntuales; sueño, ánimo 1–5 y notas. Se permite corregir la misma entrada diaria conservando su ID. Fatiga queda fuera de esta versión.
- Fechas y días de misión coherentes en UTC; respetar `as_of` y no filtrar información futura hacia una vista histórica.
- La demostración es sintética. No presentar pacientes terrestres como astronautas ni el prototipo como diagnóstico médico validado.
- Mantener el funcionamiento local independiente del backend y la separación entre componentes, hooks y fuente de datos. No sustituir una API fallida por mocks silenciosamente.

## 6. Forma de trabajar

1. Inspecciona el checkout y los documentos antes de modificar archivos. Resume el contexto y los límites en pocas líneas.
2. Presenta una dirección visual nueva: composición, tipografía, paleta de marca/estados y navegación. Haz hasta tres preguntas breves si falta una decisión de producto de impacto real; no pidas aprobación para cada detalle de CSS.
3. Implementa el rediseño completo del frontend en esa dirección. Puedes sustituir `AppShell`, `SectionPlaceholder`, páginas y estilos por componentes nuevos. Mantén React, TypeScript, Vite, Tailwind, Lucide, Recharts y los adaptadores tipados salvo cambio justificado y acordado.
4. Usa las observaciones de `docs/examples/mission_seed.json` y los casos compartidos para contenido de demostración. Amplía mocks de presentación con trazabilidad cuando sea necesario; no crees datos clínicos o cálculos que aparenten evidencia nueva.
5. Comprueba estados vacíos, errores, ausencia de análisis, observaciones de días diferentes, navegación, refresh, Back/Forward y controles reales. Cada interacción visible debe tener una conducta definida.
6. Ejecuta `npm ci`, `npm run typecheck` y `npm run build` según corresponda. Abre el resultado y revisa escritorio/móvil/teclado con las herramientas disponibles. Distingue verificaciones ejecutadas de las pendientes; no afirmes evaluación visual si no pudiste ver la aplicación.
7. Actualiza `frontend/README.md` para describir el resultado y `docs/design/redesign_rationale.md` para registrar tokens, decisiones HCI y comprobaciones. Los criterios de comportamiento se conservan; las referencias a la apariencia rechazada se sustituyen.
8. Entrega un resumen de archivos, comandos, verificaciones, limitaciones y próximos pasos. Mantén el PR #24 como lugar de revisión. No integres en `main` ni cierres issues sin aprobación final del usuario.

## Resultado esperado

Un frontend de AstroHealth completamente rediseñado, con cuatro vistas coherentes, datos sintéticos útiles para evaluar el diseño, colores funcionales claros y fundamentos HCI comprobables. El usuario debe poder ver una propuesta nueva y decidir sobre ella; la integración con Jhonatan y el trabajo de datos de Ismael deben seguir siendo viables.
