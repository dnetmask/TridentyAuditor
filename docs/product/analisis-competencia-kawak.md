# TridentyAuditor — Recomendaciones post-análisis de competencia (Kawak)

> Contexto: análisis de inteligencia de mercado realizado navegando la cuenta real
> de Netmask en Kawak (sin datos de clientes/proyectos, solo estructura de producto).
> Este documento resume qué defender, qué reforzar y qué NO copiar, para pegar como
> contexto en Claude Code y usarlo como backlog de decisiones de producto.
> Fuente: 3 rondas de recorrido en Kawak (SGSI, Riesgos y Oportunidades, Documentación,
> Auditorías e Inspecciones, Mejoramiento Continuo, Contexto de la Organización, Intel Hub).

---

## 1. Propuesta de valor real — CONFIRMADA, no tocar el mensaje

Estos tres diferenciadores quedaron verificados con evidencia directa (no solo supuestos)
y son el eje del discurso comercial de migración:

1. **Asistente / recorrido guiado (Ruta SGSI / Ruta CNO).** Recorrí las 7 apps
   funcionales de Kawak (Seguridad de la Información, Riesgos y Oportunidades,
   Documentación, Auditorías e Inspecciones, Mejoramiento Continuo, Contexto de la
   Organización, Intel Hub) y **ninguna tiene un wizard que desbloquee fases contra
   evidencia obligatoria**. Kawak tiene todas las piezas pero dispersas — el usuario
   debe saber en qué orden navegarlas. Este es el diferenciador más limpio: no lo
   diluyas, resáltalo en cada demo.
2. **Integridad documental verificable (firma + hash + estampado).** En Kawak
   encontré una matriz de roles Elabora/Revisa/Aprueba, pero **a nivel de
   configuración por cargo**, sin traza de ejecución (el historial de revisión que
   abrí estaba vacío), sin hash visible, sin PDF estampado con marca de agua
   BORRADOR/OBSOLETO/Copia no controlada en ninguna pantalla. Mantén el sello
   SHA-256 verificado en cada descarga como argumento diferenciador de auditoría
   forense/legal.
3. **Motor único multinorma vs. suite fragmentada.** Kawak son 8 apps
   independientes (recarga de página completa, sin núcleo compartido
   dominio→control→evidencia). Tu motor único (una norma por tenant, mismo core)
   es arquitectónicamente más simple de mantener y de auditar. Sigue siendo cierto
   y es más fácil de explicar en una demo técnica.

---

## 2. Matices que hay que ajustar en el discurso (no son gaps, son precisión)

- **"Kawak no tiene indicadores" → falso, hay que precisar.** Kawak tiene un
  BI real ("Intel Hub", parece Metabase/Looker embebido) con 4 dashboards
  (Inspecciones, Gestión Documental, Mejoramiento, Auditorías), filtros por
  Sede/Proceso/Tipo/Empresa, y un gauge de "% vencidos". **Pero mide vigencia
  documental (¿está vencido o no?), no % de cumplimiento normativo real
  (evidencia aprobada sobre SoA + asistente + matriz legal).** El mensaje correcto
  es: "Kawak mide higiene documental; TridentyAuditor mide madurez real de
  implementación del SGSI." No digas que Kawak no tiene reportes — di que mide
  otra cosa.
- **CAPA y auditoría interna de Kawak son más granulares en algunos puntos.**
  Su módulo de Auditorías separa Itinerarios / Informes de hallazgos / Informe
  Final / **Evaluación de auditores** / Cierre — y su CAPA ("Mejoramiento
  Continuo") trackea **% de avance y costo** de cada acción, con Análisis de
  causas y Plan de acción como pasos formales. Tu MOD·AUD hoy solo dice
  "hallazgos clasificados + CAPA con cierre verificable" — un cliente que venga
  de Kawak puede extrañar estos dos puntos.
- **Disposición de registros (retención) también existe en Kawak**, así que no
  es un diferenciador tan fuerte como parecía en el MD original — ambos lo tienen
  a nivel de estructura (aunque no confirmé legal hold en Kawak).

---

## 3. Recomendaciones de producto (backlog sugerido)

### Prioridad alta — cierran gaps reales sin diluir la propuesta de valor
- [ ] **Evaluación de auditores** dentro de MOD·AUD: campo simple de calificación
  del auditor líder al cerrar la auditoría (no hace falta un submódulo completo,
  basta un score + comentario en el cierre).
- [ ] **% de avance y costo estimado** en las acciones CAPA de MOD·AUD, para
  paridad funcional directa con "Mejoramiento Continuo" de Kawak sin salir de tu
  núcleo único (evita crear un módulo transversal separado; mantenlo ligado a
  hallazgo → control, que es tu ventaja arquitectónica).
- [ ] **Dashboard de "higiene documental"** (documentos vencidos / próximos a
  vencer / promedio de días de implementación) como complemento — no reemplazo —
  del indicador de cumplimiento en vivo. Así cubres ambas lecturas (higiene +
  madurez real) y neutralizas el único punto donde Kawak se ve "más ejecutivo".

### Prioridad media — refuerzan el diferenciador ya validado
- [ ] Explicitar visualmente en la Ruta SGSI/CNO el contraste con un
  "checklist plano": mostrar en el propio producto (banner o tour) que otras
  plataformas no bloquean el avance sin evidencia — conviértelo en una función
  demostrable en la demo, no solo un argumento de venta.
- [ ] Confirmar/reforzar en el material comercial que el sello SHA-256 y el
  historial de aprobación son **verificables por el propio cliente** (botón
  "verificar integridad" visible), ya que en Kawak esa verificación no es
  visible para el usuario final en ninguna pantalla que recorrí.

### Prioridad baja / evaluar caso a caso
- [ ] Legal hold explícito en retención y disposición (Kawak tiene disposición
  de registros pero no confirmé legal hold — si ya lo tienes, resáltalo
  como diferenciador adicional).
- [ ] Matriz de partes interesadas / análisis de contexto (clausula 4 ISO) como
  módulo propio si algún cliente enterprise lo exige en due diligence — Kawak
  lo tiene en "Contexto de la Organización".

---

## 4. Qué NO copiar de Kawak

- **No fragmentar en apps independientes.** La dispersión en 8 apps es una
  debilidad de Kawak (recarga de página, sin hilo conductor), no un patrón a
  imitar. Todo nuevo módulo debe colgar del mismo núcleo dominio→control→evidencia.
- **No mover riesgos/incidentes/CAPA a un motor "genérico transversal"
  desacoplado de los controles.** En Kawak esto obliga a "seleccionar el sistema
  sobre el cual se desea trabajar" antes de operar — es exactamente el tipo de
  fricción que tu arquitectura evita.
- **No sacrificar el asistente guiado por parecerte "más simple" un enfoque de
  módulos sueltos.** Es tu diferenciador más defendible y confirmado.

---

*Documento de producto interno de Netmask · inteligencia de mercado basada en
recorrido real de Kawak (cuenta propia, sin datos de clientes/proyectos) ·
para uso en decisiones de backlog de TridentyAuditor.*
