'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { getWebApp, supportsFeature, safeCall } from '../core';
import type { EventType } from '../types';

export function useGyroscope(refreshRate: number = 1000) {
  const isAvailable = supportsFeature('Accelerometer');

  const [x, setX] = useState(0);
  const [y, setY] = useState(0);
  const [z, setZ] = useState(0);
  const [isStarted, setIsStarted] = useState(false);

  const startedRef = useRef(false);
  const handlerRef = useRef<(() => void) | null>(null);

  const start = useCallback(() => {
    if (!isAvailable || startedRef.current) return;
    const wa = getWebApp();
    if (!wa) return;

    const rate = Math.max(20, Math.min(1000, refreshRate));
    safeCall(() => {
      wa.Gyroscope.start({ refresh_rate: rate }, (started) => {
        if (started) {
          startedRef.current = true;
          setIsStarted(true);
        }
      });
    }, undefined);
  }, [isAvailable, refreshRate]);

  const stop = useCallback(() => {
    if (!isAvailable || !startedRef.current) return;
    const wa = getWebApp();
    if (!wa) return;

    safeCall(() => {
      wa.Gyroscope.stop(() => {
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
      setX(wa.Gyroscope.x);
      setY(wa.Gyroscope.y);
      setZ(wa.Gyroscope.z);
    };
    handlerRef.current = handler;

    wa.onEvent('gyroscopeChanged' as EventType, handler);

    return () => {
      wa.offEvent('gyroscopeChanged' as EventType, handler);
      if (startedRef.current) {
        safeCall(() => wa.Gyroscope.stop(), undefined);
        startedRef.current = false;
      }
    };
  }, [isAvailable]);

  return { x, y, z, isStarted, start, stop, isAvailable };
}
