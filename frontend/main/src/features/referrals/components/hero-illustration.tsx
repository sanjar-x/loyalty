import Image from 'next/image';

const AVATARS = [
  { src: '/icons/invite-friends/1-avatar.webp', w: 51, h: 51, style: { left: 68, top: 10 } },
  { src: '/icons/invite-friends/2-avatar.webp', w: 50, h: 50, style: { left: 28, top: 78 } },
  { src: '/icons/invite-friends/3-avatar.webp', w: 54, h: 53, style: { left: 65, top: 148 } },
  { src: '/icons/invite-friends/4-avatar.webp', w: 50, h: 50, style: { right: 54, top: 10 } },
  { src: '/icons/invite-friends/5-avatar.webp', w: 55, h: 55, style: { right: 24, top: 75 } },
  { src: '/icons/invite-friends/6-avatar.webp', w: 50, h: 50, style: { right: 67, top: 146 } },
] as const;

export function HeroIllustration() {
  return (
    <div className="pointer-events-none relative my-2 h-[241px] w-full" aria-hidden="true">
      {AVATARS.map((avatar) => (
        <Image
          key={avatar.src}
          src={avatar.src}
          alt=""
          width={avatar.w}
          height={avatar.h}
          className="absolute rounded-full"
          style={avatar.style}
          priority
        />
      ))}

      <div
        className="absolute left-1/2 top-[52px] grid h-[108px] w-[108px] -translate-x-1/2 place-items-center rounded-full bg-white"
      >
        <Image
          src="/icons/invite-friends/7-avatar.webp"
          alt=""
          width={100}
          height={100}
          className="h-[100px] w-[100px] rounded-full"
          priority
        />
      </div>
    </div>
  );
}
