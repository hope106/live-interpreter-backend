# Gemini Live Interpreter 프로젝트 분석

## 개요
- Vite + React 19 기반의 실시간 한↔영 음성 동시 통역 데모.
- Google Gemini Live API(`@google/genai`)를 사용해 양방향 음성 스트리밍, 번역, 음성 합성을 처리.
- 단일 페이지 앱으로 `App.tsx`가 대부분의 로직을 담당.

## 기술 스택 및 구성
- **프론트엔드**: React 19, TypeScript, Vite, Tailwind CSS(CDN), Lucide 아이콘.
- **오디오 처리**: Web Audio API(`AudioContext`, `AnalyserNode`, `GainNode`, `ScriptProcessorNode`), custom PCM 변환 유틸.
- **AI 연동**: `GoogleGenAI` 라이브 연결(`ai.live.connect`) + 모델 `gemini-2.5-flash-native-audio-preview-09-2025`.
- **환경설정**:
  - `vite.config.ts`에서 `GEMINI_API_KEY`를 `process.env`에 주입하도록 설계.
  - `App.tsx`는 아직 `"YOUR_API_KEY_HERE"` 하드코딩 → 실제 배포 시 env 값 사용하도록 수정을 고려.
  - `metadata.json`으로 마이크 권한을 명시(프레임 임베드 환경 대비).

## 핵심 파일별 역할
### `App.tsx`
1. **상태 관리**
   - `ConnectionState`, 채팅 기록(`messages`), 실시간 텍스트 버퍼(`streamingUserText`, `streamingModelText`), 음량/뮤트, 에러 등.
   - 실시간 전사 누적용 `useRef`를 사용하여 콜백 간 공유.
2. **오디오 파이프라인**
   - 마이크 입력용/출력용 `AudioContext` 분리, ScriptProcessor로 PCM 추출, `createPcmBlob`으로 인코딩 후 세션에 전송.
   - 출력은 모델이 주는 base64 PCM을 `decodeAudioData`로 복호화해 재생 큐를 구성(`nextStartTimeRef`로 끊김 최소화).
3. **Gemini Live 세션**
   - `connectToGemini`에서 컨텍스트/권한/세션 생성, 콜백(`onopen`, `onmessage`, `onclose`, `onerror`) 정의.
   - `onmessage`에서 입력/출력 전사 누적, 턴 종료 시 `messages`에 커밋, 오디오 출력 및 인터럽트 처리.
4. **UI**
   - 상단 헤더에 연결 상태 표시, 좌측 패널은 제어(시작/중지, mute, volume) 및 시각화, 우측 패널은 `Transcript`.
   - Tailwind 클래스로 레이아웃과 상태별 스타일을 구현.
5. **클린업**
   - `stopAudio`, `handleDisconnect`로 오디오 노드 및 세션 상태를 정리; 연결 종료·에러 시 호출.

### `components/Transcript.tsx`
- 채팅 기록과 실시간 버퍼를 풍선 형태로 표시, `useEffect`로 자동 스크롤 유지.
- `lucide-react` 아이콘 사용, 사용자/모델 메시지를 대칭 레이아웃으로 구분.

### `components/Visualizer.tsx`
- `AnalyserNode` 데이터를 `<canvas>`에 파형으로 그림.
- 활성 상태가 아니면 평평한 라인을 렌더링하여 상태 피드백 제공.

### `utils/audioUtils.ts`
- PCM 샘플링 상수, Float32 → Int16 변환, base64 ↔ ArrayBuffer 변환.
- Gemini Live API에서 기대하는 포맷으로 Blob 생성 및 모델 응답 오디오 디코드.

### 그 외
- `index.html`은 Tailwind CDN, Google Fonts, import map 설정.
- `tsconfig.json`은 `bundler` 모듈 해석과 `jsx: react-jsx`.
- `metadata.json`으로 앱 설명과 마이크 권한 명시(웹 호스팅 시 사용).

## 동작 흐름 요약
1. 사용자가 “Start Session”을 누르면 `connectToGemini` 실행 → 오디오 컨텍스트/시각화 노드 생성, 마이크 권한 획득.
2. Gemini Live 세션 연결 후 ScriptProcessor가 마이크 데이터를 잡아 PCM Blob으로 변환하고 `session.sendRealtimeInput`으로 전송.
3. `onmessage`에서 모델이 보낸 입력/출력 전사 텍스트와 오디오 스트림을 실시간으로 반영.
4. 턴이 끝나면 `messages`에 양측 발화를 저장하여 `Transcript`가 갱신.
5. “Stop Session” 또는 오류 발생 시 오디오/세션 리소스를 정리하고 상태 초기화.

## 제약 및 주의사항
- API 키가 코드에 하드코딩되어 있어 실제 배포 전 환경 변수 사용 방식으로 교체 필요.
- ScriptProcessorNode는 최신 브라우저에서 레거시 API → AudioWorklet으로 교체 고려.
- 네트워크/브라우저 환경에서 마이크 권한과 HTTPS 요구사항을 만족해야 함.
- 모델 응답이 인터럽트될 때만 모델 텍스트를 비워 사용자 텍스트는 유지하도록 설계됨.

## 개선 아이디어
1. `connectToGemini` 호출 시 API 키 유효성 검증 및 UI에서 입력받는 방식 제공.
2. AudioWorklet 기반 전처리로 지연(latency) 감소 및 브라우저 호환성 강화.
3. 메시지 저장/내보내기, 언어 감지 결과 UI 피드백 등 UX 확장.
4. 테스트 작성: 오디오 없이 상태 전환/메시지 로직을 유닛 테스트로 검증.
5. 오류 상태에 대한 세분화(권한 거부, 네트워크 끊김 등)와 사용자 안내 메시지 추가.
