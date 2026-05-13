● Отлично! Раз USB можно форматировать — сделаем идеальный бэкап с сохранением всех прав, xattr, ACL и симлинков. Используем ext4 и rsync
  (можно дописывать изменения потом инкрементально — очень удобно).

  ⚠️ Сначала убедись, что на Ventoy-флешке нет нужных ISO — форматирование всё удалит.

  --------------------------------------------------------------------------------------------------------------------------------------------

  1. Отмонтируй и отформатируй USB

   sudo umount /dev/sda1 2>/dev/null
   sudo umount /dev/sda2 2>/dev/null

   # Удаляем старую разметку (Ventoy) и создаём одну партицию на весь диск
   sudo wipefs -a /dev/sda
   sudo parted /dev/sda --script mklabel gpt mkpart backup ext4 1MiB 100%
   sudo mkfs.ext4 -L CACHYBACKUP /dev/sda1

  Проверь:

   lsblk -f /dev/sda

  Должно быть sda1 ext4 CACHYBACKUP.

  2. Смонтируй

   sudo mkdir -p /mnt/backup
   sudo mount /dev/sda1 /mnt/backup
   sudo chown $USER:$USER /mnt/backup

  3. Делаем полный бэкап через rsync

   sudo rsync -aAXHv --info=progress2 \
     --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/swapfile","/var/cache/pacman/pkg/*","/home/*/
  .cache/*","/var/tmp/*"} \
     / /mnt/backup/cachyos-root/

  Флаги: -a архив, -A ACL, -X xattr, -H hardlinks, -v verbose.

  4. Сохрани метаданные (для восстановления загрузчика)

   cd /mnt/backup
   pacman -Qqe  | sudo tee pkglist-native.txt
   pacman -Qqem | sudo tee pkglist-aur.txt
   sudo cp /etc/fstab fstab.backup
   sudo lsblk -f > lsblk.txt
   sudo efibootmgr -v > efibootmgr.txt
   sudo blkid > blkid.txt
   uname -r > kernel.txt
   sync

  5. Безопасно отмонтируй

   sudo umount /mnt/backup

  --------------------------------------------------------------------------------------------------------------------------------------------

  Инкрементальное обновление бэкапа (в будущем)

  Подключи USB и повтори ту же команду rsync — скопируются только изменения, очень быстро. Добавь --delete чтобы удалённые файлы убирались и в
  бэкапе:

   sudo rsync -aAXHv --delete --info=progress2 \
     --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/swapfile","/var/cache/pacman/pkg/*","/home/*/
  .cache/*","/var/tmp/*"} \
     / /mnt/backup/cachyos-root/

  --------------------------------------------------------------------------------------------------------------------------------------------

  Восстановление на том же (или новом) железе

   1. Загрузись с CachyOS Live USB (придётся сначала на другой флешке сделать Ventoy/Live).
   2. Разметь диск и создай ФС как было:

   sudo mkfs.fat -F32 /dev/nvme0n1p1          # EFI /boot
   sudo mkfs.f2fs -f /dev/nvme0n1p2           # корень

   1. Смонтируй цель и бэкап:

   sudo mount /dev/nvme0n1p2 /mnt
   sudo mkdir -p /mnt/boot
   sudo mount /dev/nvme0n1p1 /mnt/boot
   sudo mkdir -p /media/usb && sudo mount /dev/sda1 /media/usb

   1. Восстанови файлы:

   sudo rsync -aAXHv --info=progress2 /media/usb/cachyos-root/ /mnt/

   1. Почини fstab и загрузчик:

   sudo genfstab -U /mnt | sudo tee /mnt/etc/fstab
   sudo arch-chroot /mnt

   # CachyOS обычно использует systemd-boot + limine/GRUB. Проверь /boot/loader/ или /boot/grub/:
   ls /boot

   # Для systemd-boot:
   bootctl install

   # Для GRUB (если /boot/grub существует):
   # grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=CachyOS
   # grub-mkconfig -o /boot/grub/grub.cfg

   mkinitcpio -P
   exit
   sudo umount -R /mnt
   sudo reboot

  --------------------------------------------------------------------------------------------------------------------------------------------

  Совет

  Положи рядом с бэкапом CachyOS Live ISO (~2–3 ГБ) — тогда с одной флешки сможешь и загрузиться, и восстановиться. Для этого либо оставь 5 ГБ
  под второй FAT32 раздел при форматировании, либо используй dd ISO на ту же флешку после бэкапа (сложнее).

  Хочешь — покажу как сделать двухраздельную флешку: один раздел с Live-ISO для загрузки, второй с бэкапом?
