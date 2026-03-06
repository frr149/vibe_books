

  ---
  Prompt: Anti-Hallucination Defenses for API Development

  # Instrucción: Defensas anti-alucinación obligatorias

  Cuando generes código que consume o expone APIs (DTOs, modelos, schemas, fixtures, tests),
  aplica TODAS estas defensas mecánicas. No son opcionales.

  ## Contexto

  Un LLM puede inventar campos de API inexistentes y construir toda la cadena
  (DTO → fixture → test) para que parezca legítimo. 90 tests verdes, todo ficción.
  Las siguientes reglas hacen que ese escenario sea mecánicamente imposible.

  ---

  ## 1. Strict Mode en TODOS los modelos/DTOs

  Todo modelo que deserialice datos externos DEBE rechazar campos desconocidos.

  ```python
  # Python (Pydantic)
  from pydantic import BaseModel, ConfigDict

  class ProfileResponse(BaseModel):
      model_config = ConfigDict(extra='forbid')  # OBLIGATORIO
      id: int
      name: str

  // TypeScript (Zod)
  const ProfileSchema = z.object({
    id: z.number(),
    name: z.string(),
  }).strict();  // OBLIGATORIO

  // Rust (serde)
  #[derive(Deserialize)]
  #[serde(deny_unknown_fields)]  // OBLIGATORIO
  struct ProfileResponse {
      id: i64,
      name: String,
  }

  // Swift
  enum CodingKeys: String, CodingKey, CaseIterable {  // CaseIterable OBLIGATORIO
      case id, name
  }

  Red flags que NUNCA debes generar:
  - Any, dynamic, dict sin tipar, serde_json::Value como tipo de campo
  - as type assertions en datos de API (TypeScript)
  - extra='allow' o extra='ignore' (Pydantic)
  - Decodable sin CodingKeys (Swift)

  ---
  1. Fixtures con proveniencia — NUNCA inventar datos

  PROHIBIDO: Escribir JSON de respuesta de API a mano o "de memoria".

  OBLIGATORIO: Toda fixture debe tener uno de estos orígenes verificables:

  - Captura real: grabada con VCR.py, MSW, Polly.js, wiremock-rs o similar
  - Copia documentada: extraída de la documentación oficial de la API con referencia
  - Script de captura: make capture o equivalente que llame a la API real y guarde el JSON

  # BIEN — fixture con proveniencia
  # Capturado de GET /api/v1/profile/42 el 2025-01-15
  # Script: make capture-profile
  REAL_PROFILE_RESPONSE = json.loads(
      (Path(__file__).parent / "fixtures/real/profile_42.json").read_text()
  )

  # MAL — fixture inventada
  FAKE_RESPONSE = {"id": 42, "name": "Test", "active_flags": ["premium"]}
  # ¿De dónde sale active_flags? ¿Existe ese campo? Nadie lo sabe.

  Si no tienes acceso a la API real todavía, márcalo explícitamente:

  # TODO(contract): fixture sintética — reemplazar con captura real antes de producción
  # Campos basados en: https://docs.example.com/api#profile (consultado 2025-01-15)

  ---
  3. Contract tests — DTOs vs realidad

  Debe existir AL MENOS un test que compare los campos del DTO contra datos reales:

  # Python — contract test
  def test_profile_schema_matches_real_response():
      """Verifica que el DTO no tiene campos fantasma ni le faltan campos reales."""
      real = json.loads(Path("fixtures/real/profile.json").read_text())
      dto_fields = set(ProfileResponse.model_fields.keys())
      real_fields = set(real.keys())

      phantom = dto_fields - real_fields  # Campos que inventó el LLM
      missing = real_fields - dto_fields  # Campos reales no mapeados

      assert not phantom, f"PHANTOM fields (no existen en API real): {phantom}"
      assert not missing or missing == KNOWN_UNCONSUMED, \
          f"MISSING fields (existen en API pero no en DTO): {missing}"

  // TypeScript — contract test
  test('ProfileSchema matches real API response', () => {
    const real = require('./fixtures/real/profile.json');
    // Si hay campos extra o faltan campos, Zod.strict() falla
    expect(() => ProfileSchema.parse(real)).not.toThrow();
  });

  ---
  4. Pipeline de captura en CI

  # Makefile
  capture:        # Graba respuestas reales de la API
        python scripts/capture_fixtures.py

  doctor:         # Valida DTOs contra fixtures reales
        pytest tests/contract/ -v

  ci: lint test doctor   # doctor es parte del CI

  ---
  5. Runtime: loguear fallos de deserialización

  NUNCA silenciar errores de parsing. Si la API cambia, hay que enterarse:

  # BIEN — logging en decode failure
  try:
      profile = ProfileResponse.model_validate(data)
  except ValidationError as e:
      logger.error("Schema drift detected in /profile", extra={"errors": e.errors()})
      raise

  # MAL — silencioso
  profile = ProfileResponse.model_validate(data, strict=False)  # traga errores

  ---
  Checklist antes de entregar código de API

  - Todos los DTOs/modelos tienen strict mode activado
  - No hay Any/dict/dynamic/Value en campos de modelos de API
  - Las fixtures tienen origen documentado (captura real o referencia a docs)
  - Existe al menos un contract test (DTO fields vs fixture real fields)
  - Los fallos de deserialización se loguean, no se silencian
  - No hay campos en los DTOs que no puedas demostrar que existen en la API real

  ---
  Principio rector

  Si un campo no aparece en una respuesta real capturada o en la documentación oficial
  enlazada, NO EXISTE. No lo añadas "por si acaso". No lo inventes "porque tiene sentido".
  El camino incorrecto debe ser imposible, no prohibido.

  ---