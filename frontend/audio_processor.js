// frontend/audio_processor.js
// AudioWorkletProcessor — runs in audio rendering thread
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._inputSampleRate = 44100; // will be overridden
    this._outputSampleRate = 16000;
    this._chunkSamples = 1600; // 100ms at 16kHz
  }
 
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
 
    const channelData = input[0]; // mono
    this._inputSampleRate = sampleRate; // AudioWorkletGlobalScope.sampleRate
 
    // Downsample: linear interpolation
    const ratio = this._inputSampleRate / this._outputSampleRate;
    for (let i = 0; i < channelData.length; i += ratio) {
      this._buffer.push(channelData[Math.floor(i)]);
    }
 
    // Emit chunks
    while (this._buffer.length >= this._chunkSamples) {
      const chunk = this._buffer.splice(0, this._chunkSamples);
      // Convert Float32 → Int16
      const pcm16 = new Int16Array(chunk.length);
      for (let j = 0; j < chunk.length; j++) {
        const s = Math.max(-1, Math.min(1, chunk[j]));
        pcm16[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      this.port.postMessage({ type: 'pcm', buffer: pcm16.buffer }, [pcm16.buffer]);
    }
    return true;
  }
}
 
registerProcessor('pcm-processor', PCMProcessor);
