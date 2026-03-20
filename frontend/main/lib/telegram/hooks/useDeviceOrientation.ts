'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { getWebApp, supportsFeature, safeCall } from '../core';
import type { EventType } from '../types';

export function useDeviceOrientation(
  refreshRate: number = 1000,
  needAbsolute: boolean = false,
) {
  const isAvailable = supportsFeature('Accelerometer');

  const [alpha, setAlpha] = useState(0);
  const [beta, setBeta] = useState(0);
  const [gamma, setGamma] = useState(0);
  const [absolute, setAbsolute] = useState(false);
  const [isStarted, setIsStarted] = useState(false);

  const startedRef = useRef(false);
  const handlerRef = useRef<(() => void) | null>(null);

  const start = useCallback(() => {
    if (!isAvailable || startedRef.current) return;
    const wa = getWebApp();
    if (!wa) return;

    const rate = Math.max(20, Math.min(1000, refreshRate));
    safeCall(() => {
      wa.DeviceOrientation.start(
        { refresh_rate: rate, need_absolute: needAbsolute },
        (started) => {
          if (started) {
            startedRef.current = true;
            setIsStarted(true);
          }
        },
      );
    }, undefined);
  }, [isAvailable, refreshRate, needAbsolute]);

  const stop = useCallback(() => {
    if (!isAvailable || !startedRef.current) return;
    const wa = getWebApp();
    if (!wa) return;

    safeCall(() => {
      wa.DeviceOrientation.stop(() => {
        startedRef.current = false;
        setIsStarted(false);
      });
    }, undefined);
  }, [isAvailable]);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    const handler = () => {
      setAlpha(wa.DeviceOrientation.alpha);
      setBeta(wa.DeviceOrientation.beta);
      setGamma(wa.DeviceOrientation.gamma);
      setAbsolute(wa.DeviceOrientation.absolute);
    };
    handlerRef.current = handler;

    wa.onEvent('deviceOrientationChanged' as EventType, handler);

    return () => {
      wa.offEvent('deviceOrientationChanged' as EventType, handler);
      if (startedRef.current) {
        safeCall(() => wa.DeviceOrientation.stop(), undefined);
        startedRef.current = false;
      }
    };
  }, [isAvailable]);

  return { alpha, beta, gamma, absolute, isStarted, start, stop, isAvailable };
}
