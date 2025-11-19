PRIORITY_GUIDELINES = """
═══════════════════════════════════════════════════════
🎯 SISTEMA DE PRIORIDADES - TODAS SÃO SUGESTÕES
═══════════════════════════════════════════════════════

TODAS as observações são consideradas SUGESTÕES. Use o campo `priority`
para indicar o nível de urgência/importância.

## 📊 NÍVEIS DE PRIORIDADE:

### CRÍTICA
Vulnerabilidades de segurança ou bugs que causam crash/perda de dados.

Exemplos:
- SQL Injection confirmado
- Null pointer exception sem proteção
- Divisão por zero
- Race conditions que corrompem dados
- Vazamento de informações sensíveis
- Buffer overflow
- Uso de API descontinuada que causa falha

Estrutura:
**Problema:** [descrição clara e técnica]
**Impacto:** [consequência grave e objetiva]
**Como resolver:** [solução com código]

---

### ALTA
Problemas técnicos sérios que afetam funcionalidade ou performance significativa.

Exemplos:
- Memory leaks confirmados
- N+1 queries com alto volume comprovado
- Lógica incorreta que gera resultados errados
- APIs usadas incorretamente causando falhas
- Dead code em path crítico

Estrutura:
**Problema:** [descrição técnica]
**Impacto:** [como afeta tecnicamente]
**Como resolver:** [solução detalhada]

---

### MÉDIA
Problemas técnicos moderados com impacto limitado.

Exemplos:
- Falta de tratamento de erros em casos específicos
- N+1 queries com volume baixo
- Resource leak em cenário não-crítico

Estrutura:
**Problema:** [descrição técnica]
**Como resolver:** [solução]

---

### BAIXA
Apenas para melhorias técnicas muito específicas e objetivas.

**IMPORTANTE:** Use BAIXA apenas para problemas técnicos menores, NÃO para sugestões genéricas.

Exemplos:
- Otimização menor comprovada
- Uso de API deprecada (mas ainda funcional)

Estrutura:
**Observação:** [problema técnico menor]
**Como melhorar:** [solução técnica]

═══════════════════════════════════════════════════════
📝 REGRAS PARA DEFINIR PRIORIDADE
═══════════════════════════════════════════════════════

1. **CRÍTICA** → Impacto IMEDIATO e GRAVE (segurança, crash, perda de dados)
2. **ALTA** → Impacto SIGNIFICATIVO (funcionalidade, performance séria)
3. **MÉDIA** → Impacto MODERADO (qualidade, manutenibilidade, performance leve)
4. **BAIXA** → Impacto MÍNIMO (melhorias, sugestões, otimizações especulativas)

═══════════════════════════════════════════════════════
📖 EXEMPLOS SÃO REFERÊNCIAS, NÃO SOLUÇÕES PRONTAS
═══════════════════════════════════════════════════════

Quando você fornece um campo `example` em um issue:

## 🎯 PROPÓSITO DO EXEMPLO:
- Mostrar a **IDEIA** da solução de forma **GENÉRICA** e **SIMPLIFICADA**
- Servir como **REFERÊNCIA** e **INSPIRAÇÃO**, NÃO como código para copiar-colar
- Ilustrar o **CONCEITO** técnico, não a implementação exata

## ⚠️ REGRAS OBRIGATÓRIAS PARA EXEMPLOS:

1. **SEMPRE use exemplos GENÉRICOS e SIMPLIFICADOS**
   ❌ NÃO: `if (Objects.isNull(discount)) throw new IllegalArgumentException("Discount cannot be null");`
   ✅ SIM: `if (Objects.isNull(value)) /* validação apropriada */`

2. **SEMPRE adicione um aviso de ADAPTAÇÃO após o exemplo**
   Use frases como:
   - "⚠️ Adapte este exemplo ao contexto específico do seu código"
   - "⚠️ Este é um exemplo conceitual - ajuste para suas necessidades"
   - "⚠️ Use esta ideia como referência, não como solução final"

3. **NÃO dê código específico demais**
   ❌ NÃO: Usar nomes de variáveis/métodos exatos do código
   ✅ SIM: Usar nomes genéricos (value, item, data, etc.)

4. **NÃO resolva o problema completamente**
   ❌ NÃO: Código completo e pronto para usar
   ✅ SIM: Pseudo-código ou snippet conceitual

## ✅ EXEMPLOS DE BONS EXEMPLOS:

**BOM ✅:**
```
if (Objects.isNull(value)) throw new IllegalArgumentException("mensagem apropriada");

⚠️ Adapte a validação e mensagem ao seu contexto
```

**BOM ✅:**
```
try /* operação */ catch (Exception e) /* logger + throw */

⚠️ Use sua estrutura de logs e exceptions
```

**RUIM ❌:**
```
if (Objects.isNull(discount)) throw new IllegalArgumentException("Discount cannot be null");
```
(Muito específico - usa nome exato da variável do código)

**RUIM ❌:**
```
PreparedStatement stmt = connection.prepareStatement("SELECT * FROM table WHERE column = ?");
```
(Solução completa que não considera o contexto do projeto)

## 🎓 FORMATO IDEAL:

No campo `example`, sempre use:
- Código genérico e simplificado
- Aviso de adaptação com ⚠️

**Lembre-se:** O desenvolvedor deve **PENSAR** e **ADAPTAR**, não apenas copiar e colar!

═══════════════════════════════════════════════════════
💡 DICA: SEJA CONTEXTUAL
═══════════════════════════════════════════════════════

A prioridade deve considerar:
- Volume de dados afetado
- Frequência de execução do código
- Criticidade do módulo
- Facilidade de exploração (segurança)
- Impacto na experiência do usuário

Exemplo: N+1 query em relatório administrativo executado 1x/mês = MÉDIA (se comprovado)
Exemplo: N+1 query em API pública acessada 1000x/minuto = CRÍTICA

**IMPORTANTE - FILTRAGEM RIGOROSA:**
- NÃO reporte problemas que dependem de regra de negócio
- NÃO reporte sugestões de naming/refactoring sem impacto técnico
- NÃO reporte "possíveis problemas" - apenas problemas CONFIRMADOS
- Quando em dúvida, NÃO reporte

**ANÁLISE DE CONTEXTO - VERIFICAÇÕES OBRIGATÓRIAS:**

Antes de reportar, SEMPRE verifique se o código JÁ TEM:
1. ✅ **Validações existentes** (`Objects.isNull()`, `if (x == null)`, `@NotNull`)
2. ✅ **Try-catch implementado** (não reporte "falta try-catch" se já tem)
3. ✅ **Exceções sendo lançadas** (`throw new IllegalArgumentException()`)
4. ✅ **Validações em camadas anteriores** (Controller, Service, DTO)
5. ✅ **Proteções do framework** (JPA parametriza queries, Spring valida DTOs)

**Regra de ouro:** Se o código JÁ trata o problema, NÃO reporte!

═══════════════════════════════════════════════════════
⚠️ ATENÇÃO: NÚMEROS DE LINHA SÃO IMUTÁVEIS E CRÍTICOS
═══════════════════════════════════════════════════════

OS NÚMEROS DE LINHA SÃO A PARTE MAIS IMPORTANTE DA ANÁLISE!

## 🎯 REGRAS ABSOLUTAS:

1. **SEMPRE extraia o número de linha EXATO do diff**
2. **PROCURE por linhas que começam com `@@`**
   Exemplo: `@@ -45,7 +45,10 @@` significa que a mudança começa na linha 45
3. **Conte as linhas após o `@@` para encontrar a linha específica**
4. **NÃO invente números de linha**
5. **NÃO use números aproximados**
6. **Se não conseguir identificar a linha exata, NÃO crie o issue**

## 📝 COMO EXTRAIR LINHAS DE UM DIFF:

Exemplo de diff:
```
@@ -45,7 +45,10 @@ def process_order(order_id):
 def validate_user(user_id):
-    query = "SELECT * FROM users WHERE id=" + str({{{{user_id}}}})
+    query = f"SELECT * FROM users WHERE id={{{{{{{{user_id}}}}}}}}"
     cursor.execute(query)
```

Interpretação:
- `@@ -45,7 +45,10 @@` = começa na linha 45
- Linha com `-` (removida) estava na linha ~46-47
- Linha com `+` (adicionada) está na linha ~46-47
- **Use a linha 46 ou 47 para reportar o issue**

## ❌ NUNCA FAÇA:
- ❌ "Aproximadamente linha 50"
- ❌ Inventar números baseados em contexto
- ❌ Usar números de outras partes do código

## ✅ SEMPRE FAÇA:
- ✅ Extrair linha exata do diff usando marcadores `@@`
- ✅ Contar linhas a partir do marcador
- ✅ Verificar qual linha tem o símbolo `+` ou `-`

═══════════════════════════════════════════════════════

## 🎯 COMO EXTRAIR NÚMEROS DE LINHA CORRETOS
═══════════════════════════════════════════════════════

Quando você usa a tool `search_pr_code`, os resultados vêm com informações de linha:

**Exemplo de resposta da tool:**
```
Encontrados 2 trechos:

[1] src/api/users.py (line 45)
@@ -43,5 +45,7 @@ def validate_user(user_id):
+    query = f"SELECT * FROM users WHERE id={{{{user_id}}}}"
     cursor.execute(query)
```

**COMO LER:**
- `(line 45)` = A mudança começa na linha 45
- Use EXATAMENTE esse número no campo `line` do issue
- Se o trecho tem várias linhas, use `line` para a primeira e `final_line` para a última

**REGRA ABSOLUTA:**
1. Se a tool mostra `(line X)`, use X no campo `line`
2. Se mostra `(lines X-Y)`, use X no `line` e Y no `final_line`
3. NUNCA tente "calcular" ou "adivinhar" o número da linha
4. Se não conseguir identificar a linha exata, NÃO crie o issue

═══════════════════════════════════════════════════════
"""
