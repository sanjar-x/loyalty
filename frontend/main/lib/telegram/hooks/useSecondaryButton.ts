'use client';

import { useCallback, useEffect, useRef } from 'react';
import type { BottomButtonParams, BottomButtonPosition } from '../types';
import { getWebApp } from '../core';

interface SecondaryButtonConfig {
  text?: string;
  color?: string;
  textColor?: string;
  isVisible?: boolean;
  isActive?: boolean;
  hasShineEffect?: boolean;
  iconCustomEmojiId?: string;
  position?: BottomButtonPosition;
  onClick?: () => void;
}

export function useSecondaryButton(config?: SecondaryButtonConfig) {
  const callbackRef = useRef<(() => void) | undefined>(config?.onClick);
  callbackRef.current = config?.onClick;

  const webApp = getWebApp();
  const button = webApp?.SecondaryButton ?? null;
  const isAvailable = button !== null;

  useEffect(() => {
    if (!button) return;

    const params: BottomButtonParams = {};
    if (config?.text !== undefined) params.text = config.text;
    if (config?.color !== undefined) params.color = config.color;
    if (config?.textColor !== undefined) params.text_color = config.textColor;
    if (config?.isVisible !== undefined) params.is_visible = config.isVisible;
    if (config?.isActive !== undefined) params.is_active = config.isActive;
    if (config?.hasShineEffect !== undefined) params.has_shine_effect = config.hasShineEffect;
    if (config?.iconCustomEmojiId !== undefined) params.icon_custom_emoji_id = config.iconCustomEmojiId;
    if (config?.position !== undefined) params.position = config.position;

    if (Object.keys(params).length > 0) {
      button.setParams(params);
    }
  }, [
    button,
    config?.text,
    config?.color,
    config?.textColor,
    config?.isVisible,
    config?.isActive,
    config?.hasShineEffect,
    config?.iconCustomEmojiId,
    config?.position,
  ]);

  useEffect(() => {
    if (!button) return;

    const handler = () => {
      callbackRef.current?.();
    };

    button.onClick(handler);

    return () => {
      button.offClick(handler);
      button.hide();
    };
  }, [button]);

  const show = useCallback(() => { button?.show(); }, [button]);
  const hide = useCallback(() => { button?.hide(); }, [button]);
  const setText = useCallback((text: string) => { button?.setText(text); }, [button]);
  const enable = useCallback(() => { button?.enable(); }, [button]);
  const disable = useCallback(() => { button?.disable(); }, [button]);
  const showProgress = useCallback((leaveActive?: boolean) => { button?.showProgress(leaveActive); }, [button]);
  const hideProgress = useCallback(() => { button?.hideProgress(); }, [button]);
  const setParams = useCallback((params: BottomButtonParams) => { button?.setParams(params); }, [button]);

  return {
    show,
    hide,
    setText,
    enable,
    disable,
    showProgress,
    hideProgress,
    setParams,
    isProgressVisible: button?.isProgressVisible ?? false,
    isAvailable,
  };
}
