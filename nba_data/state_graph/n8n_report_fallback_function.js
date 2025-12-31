// n8n Function 노드: AI 리포트 생성 (폴백 체인)
//
// 폴백 순서:
// 1. Grok 4.1 Fast (메인)
// 2. Qwen 2.5 VL 72B (백업 1) - 업그레이드! 저렴하고 강력
// 3. GPT-4o-mini (백업 2)
// 4. Claude 3.5 Haiku (최후)

const axios = require('axios');

// OpenRouter API 설정
const OPENROUTER_API_KEY = $env.OPENROUTER_API_KEY;
const BASE_URL = 'https://openrouter.ai/api/v1/chat/completions';

// 폴백 모델 목록 (순서대로 시도)
const MODELS = [
  {
    name: 'Grok 4.1 Fast',
    id: 'x-ai/grok-4.1-fast',
    timeout: 10000,  // 10초
    pricing: { input: 0.20, output: 0.50 }
  },
  {
    name: 'Qwen 2.5 VL 72B',
    id: 'qwen/qwen2.5-vl-72b-instruct',
    timeout: 15000,  // 15초
    pricing: { input: 0.07, output: 0.26 }  // ⭐ 저렴하고 강력!
  },
  {
    name: 'GPT-4o-mini',
    id: 'openai/gpt-4o-mini',
    timeout: 15000,  // 15초
    pricing: { input: 0.15, output: 0.60 }
  },
  {
    name: 'Claude 3.5 Haiku',
    id: 'anthropic/claude-3.5-haiku',
    timeout: 20000,  // 20초
    pricing: { input: 0.80, output: 4.00 }
  }
];

// Event와 Context 데이터 가져오기
const event = $node["Event 구조화"].json;
const context = $node["Neo4j - Context 계산"].json;

// 프롬프트 생성
const prompt = `Generate NBA betting signal report.

Event:
${JSON.stringify(event, null, 2)}

Context:
${JSON.stringify(context, null, 2)}

Provide:
1. Impact Assessment (0-10)
2. Historical Pattern
3. Betting Implications
4. Confidence Level

Keep response concise and actionable.`;

// AI 호출 함수
async function callAI(model) {
  const headers = {
    'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
    'Content-Type': 'application/json',
    'HTTP-Referer': 'https://github.com/nba-realtime-pipeline',
    'X-Title': 'NBA Real-time Event Analyzer'
  };

  const payload = {
    model: model.id,
    messages: [
      {
        role: 'user',
        content: prompt
      }
    ],
    temperature: 0.3,
    max_tokens: 1000
  };

  try {
    console.log(`[${model.name}] Attempting...`);

    const response = await axios.post(BASE_URL, payload, {
      headers: headers,
      timeout: model.timeout
    });

    const content = response.data.choices[0].message.content;

    console.log(`[${model.name}] ✅ Success`);

    return {
      success: true,
      model: model.name,
      model_id: model.id,
      content: content,
      pricing: model.pricing
    };

  } catch (error) {
    console.error(`[${model.name}] ❌ Failed: ${error.message}`);

    return {
      success: false,
      model: model.name,
      model_id: model.id,
      error: error.message
    };
  }
}

// 폴백 체인 실행
async function runWithFallback() {
  const attempts = [];

  for (const model of MODELS) {
    const result = await callAI(model);
    attempts.push(result);

    if (result.success) {
      // 성공! 결과 반환
      return {
        json: {
          report: result.content,
          model_used: result.model,
          model_id: result.model_id,
          pricing: result.pricing,
          fallback_attempts: attempts.length,
          all_attempts: attempts
        }
      };
    }

    // 실패 - 다음 모델로
    console.log(`[Fallback] Trying next model...`);
  }

  // 모든 모델 실패
  console.error('[Fallback] All models failed!');

  return {
    json: {
      error: 'All AI models failed',
      report: `⚠️ AI 리포트 생성 실패\n\n모든 모델이 응답하지 않았습니다.\n수동 확인 필요.`,
      all_attempts: attempts,
      event: event,
      context: context
    }
  };
}

// 실행
return await runWithFallback();
