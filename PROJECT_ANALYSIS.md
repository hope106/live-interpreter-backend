# Gemini Live Interpreter 프로젝트 분석

## 1. 개요
- **목표**: Gemini Live API를 이용해 한·영 양방향 통역을 실시간으로 제공하는 웹 애플리케이션.
- **주요 특징**: 마이크 입력을 스트리밍으로 전송, 모델의 오디오/텍스트 응답을 동시에 받아 재생 및 자막 표시.
- **UI**: Tailwind CDN과 커스텀 스타일을 활용한 단일 페이지로 구성되며, 좌측은 제어/시각화, 우측은 대화 기록 영역.

## 2. 기술 스택
- **런타임/번들링**: Vite + TypeScript + React 19.
- **AI SDK**: `@google/genai`(Live API) – `GoogleGenAI`의 `live.connect`를 사용하여 양방향 세션을 생성.
- **아이콘/UI**: `lucide-react`, Tailwind.
- **오디오 처리**: Web Audio API (`AudioContext`, `AnalyserNode`, `ScriptProcessorNode`), 커스텀 PCM 인코더/디코더(`utils/audioUtils.ts`).

## 3. 파일 구조 요약
| 파일 | 역할 |
|------|------|
| `App.tsx` | 비즈니스 로직·상태 관리·UI를 모두 담당하는 메인 컴포넌트. |
| `components/Transcript.tsx` | 스트리밍 중간 결과와 확정 메시지를 함께 표시하며 자동 스크롤 제공. |
| `components/Visualizer.tsx` | 입력/출력 오디오 분석 데이터를 캔버스 파형으로 시각화. |
| `utils/audioUtils.ts` | PCM 인코딩, Base64 변환, 24kHz 단일 채널 디코딩 도우미. |
| `vite.config.ts` | `GEMINI_API_KEY` 주입, 포트/호스트 설정, 경로 별칭. |

## 4. 실시간 처리 흐름
1. **연결 준비**: `connectToGemini`에서 입력(16kHz)·출력(24kHz) 오디오 컨텍스트, 게인/분석 노드, 볼륨 상태를 초기화.
2. **마이크 캡처**: `getUserMedia`로 받은 스트림을 `ScriptProcessorNode`에 연결. `createPcmBlob`을 통해 PCM(Int16)으로 변환 후 `session.sendRealtimeInput` 호출.
3. **세션 설정**: `SYSTEM_INSTRUCTION`으로 통역 정책을 명시하고, `responseModalities: [Modality.AUDIO]`, `input/outputAudioTranscription` 옵션으로 텍스트도 함께 수신.
4. **콜백 처리**:
   - `onmessage`: 입력·출력 실시간 문장을 누적하고, 턴이 종료되면 `messages` 상태에 영구 저장.
   - 오디오 응답(`inlineData`)은 Base64 → PCM → `AudioBuffer`로 변환해 출력 큐에 배치(`nextStartTimeRef`).
   - `interrupted` 플래그가 오면 모델 응답 큐와 텍스트만 초기화해 자연스러운 인터럽트 UX를 구현.
5. **세션 종료**: `handleDisconnect`가 모든 AudioContext/노드를 안전하게 종료하고 상태를 초기화.

## 5. 상태 및 UI 구성
- **ConnectionState**: `DISCONNECTED/CONNECTING/CONNECTED/ERROR` 4단계를 UI에 뱃지로 반영.
- **스트리밍 텍스트**: `streamingUserText`, `streamingModelText`로 확정 전 문장을 따로 관리하여 Transcript에 깜박이는 커서를 제공.
- **오디오 제어**: 마이크 mute 토글, 볼륨 슬라이더, 세션 온/오프 버튼. 시각화는 `AnalyserNode`를 전달받아 Canvas에서 애니메이션.
- **에러 처리**: `setError`를 통해 메시지를 표시하고, 동시에 연결을 끊어 리소스 누수 방지.

## 6. 강점
- **명확한 시스템 지침**으로 통역 스타일을 통제하고, 턴 종료/인터럽트 로직을 섬세하게 처리.
- **리소스 정리**: `useCallback`으로 정의한 `stopAudio`를 재사용해 모든 AudioContext/노드를 일관되게 해제.
- **시각 피드백**: 입력/출력 시각화와 실시간 transcript로 사용자가 음성 상태를 즉시 확인 가능.

## 7. 개선 여지
1. **API 키 주입**: `App.tsx`에 `const apiKey = "YOUR_API_KEY_HERE";`가 하드코딩되어 있으며 Vite `define` 설정과 분리되어 있음. `.env` → `import.meta.env` 연결이 필요.
2. **오디오 워크렛으로 교체**: `ScriptProcessorNode`는 deprecated 되었으므로 AudioWorklet으로 전환하면 지연과 호환성을 개선할 수 있음.
3. **상태 분리**: `App.tsx`가 UI·로직을 모두 포함하므로, 커스텀 훅(예: `useLiveInterpreter`)으로 통신/오디오 로직을 분리하면 테스트 및 유지보수성이 향상.
4. **에러 유형 별 UX**: 현재는 텍스트만 표시하므로, 재시도 버튼/가이드 등을 추가하면 사용자 경험 향상.
5. **보안**: 마이크 권한 실패 시 별도 안내, HTTPS 요구사항 등의 가드를 추가할 필요가 있음.

## 8. 실행 방법
1. `npm install`
2. 루트에 `.env.local`을 생성하고 `GEMINI_API_KEY=...` 설정
3. `npm run dev` 후 브라우저에서 `http://localhost:3000` 접속
4. Start Session 버튼을 누르고 마이크 권한을 허용

## 9. 요약
- 본 앱은 Gemini Live API의 양방향 실시간 기능을 활용해 통역사의 역할을 자동화하는 데 집중.
- 오디오 인코딩/디코딩, 시각화, transcript 저장 등 실시간 애플리케이션에서 필요한 구성 요소가 대부분 구현되어 있음.
- 환경변수 연결 및 오디오 스트림 처리 방식 개선으로 더욱 안정적인 제품화 가능.

