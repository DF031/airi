import { useEffect, useRef } from 'react';
import { makeLive2DStageManager } from './avatar/live2dStageManager';
import { DEFAULT_MODEL_URL, DEFAULT_AVATAR_FIT } from './avatar/modelRegistry';

export default function Live2DViewer({
  modelUrl = DEFAULT_MODEL_URL,
  modelFit = DEFAULT_AVATAR_FIT,
  modelProfile = null,
}) {
  const canvasRef = useRef(null);
  const managerRef = useRef(null);
  const modelFitRef = useRef(modelFit);
  const modelProfileRef = useRef(modelProfile);
  const modelUrlRef = useRef(modelUrl);
  const loadedModelUrlRef = useRef('');

  useEffect(() => {
    modelFitRef.current = modelFit;
    managerRef.current?.updateModelFit();
  }, [modelFit]);

  useEffect(() => {
    modelProfileRef.current = modelProfile;
    managerRef.current?.updateProfile();
    managerRef.current?.updateModelFit();
  }, [modelProfile]);

  useEffect(() => {
    modelUrlRef.current = modelUrl || DEFAULT_MODEL_URL;
  }, [modelUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const manager = makeLive2DStageManager({
      canvas,
      getModelFit: () => modelFitRef.current,
      getModelProfile: () => modelProfileRef.current,
    });
    managerRef.current = manager;
    manager.updateProfile();
    loadedModelUrlRef.current = modelUrlRef.current;
    manager.initialize(modelUrlRef.current);

    return () => {
      manager.destroy();
      if (managerRef.current === manager) {
        managerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const nextUrl = modelUrl || DEFAULT_MODEL_URL;
    const manager = managerRef.current;
    if (!manager || loadedModelUrlRef.current === nextUrl) return;
    loadedModelUrlRef.current = nextUrl;
    manager.loadModel(nextUrl);
  }, [modelUrl]);

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <canvas ref={canvasRef} style={{ pointerEvents: 'auto', cursor: 'pointer', width: '100%', height: '100%' }} />
    </div>
  );
}
