# Minimal Grub Theme from KDE Neon

[Full Instructions](https://github.com/Jacksaur/Gorgeous-GRUB/blob/main/Installation.md)

- Copy theme folder to /boot/grub/themes/
- `sudo chown $USER /boot/grub/themes`
- Edit /etc/default/grub
- Add `GRUB_THEME="/boot/grub/themes/breeze/theme.txt"`
- Update grub: `sudo update-grub`
- Reboot
