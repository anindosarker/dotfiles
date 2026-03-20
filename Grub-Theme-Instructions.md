# Minimal Grub Theme from KDE Neon

[Full Instructions](https://github.com/Jacksaur/Gorgeous-GRUB/blob/main/Installation.md)

1. Create the themes directory:

```bash
sudo mkdir -p /boot/grub/themes
```

2. Copy the breeze theme from your dotfiles repo (assuming it is at `~/dotfiles`):

```bash
sudo cp -r ~/dotfiles/grub/theme/breeze /boot/grub/themes/
```

3. Set ownership so you can edit files there if needed:

```bash
sudo chown $USER /boot/grub/themes
```

4. Add the GRUB theme line to `/etc/default/grub`:

```bash
echo 'GRUB_THEME="/boot/grub/themes/breeze/theme.txt"' | sudo tee -a /etc/default/grub
```

5. Update GRUB:

```bash
sudo update-grub
```

6. Reboot:

```bash
reboot
```
