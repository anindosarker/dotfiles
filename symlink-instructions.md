## 🔗 Symlinking Dotfiles

### 1. Clone the repo

```bash
cd ~
git clone https://github.com/anindosarker/dotfiles.git
```

---

### 2. Backup existing configs

Before symlinking, back up any existing config files so you don't lose them:

```bash
mkdir -p ~/dotfiles-backup
[ -f ~/.zshrc ] && cp ~/.zshrc ~/dotfiles-backup/.zshrc
[ -d ~/.config/nvim ] && cp -r ~/.config/nvim ~/dotfiles-backup/nvim
```

Your originals will be safely saved in `~/dotfiles-backup/` before anything is overwritten.

---

### 3. Symlink `.zshrc`

Pick the file for your current distro:

**Kubuntu / Ubuntu:**

```bash
ln -sf ~/dotfiles/kubuntu/.zshrc ~/.zshrc
```

**Manjaro:**

```bash
ln -sf ~/dotfiles/manjaro/.zshrc ~/.zshrc
```

**macOS:**

```bash
ln -sf ~/dotfiles/mac/.zshrc ~/.zshrc
```

> `-s` creates a symbolic link, `-f` forces it (replaces any existing file).

---

### 4. Symlink Neovim config

```bash
mkdir -p ~/.config
ln -sf ~/dotfiles/nvim ~/.config/nvim
```

This links the entire folder, so any file added inside `~/dotfiles/nvim/` is instantly picked up by Neovim.

---

### 5. Verify the links

```bash
ls -la ~/.zshrc
ls -la ~/.config/nvim
```

You should see arrows pointing back to your dotfiles repo:

```
~/.zshrc -> /home/youruser/dotfiles/kubuntu/.zshrc
~/.config/nvim -> /home/youruser/dotfiles/nvim
```

---

### 6. Reload your shell

```bash
source ~/.zshrc
```

---

### 📝 Notes

- Always edit files inside `~/dotfiles/` and commit from there — never edit the symlink target directly.
- If you get a "file exists" error, remove the old file first (`rm ~/.zshrc`) then re-run the symlink command.
- To add a new config in the future, move it into your dotfiles folder and symlink it the same way.

---

### tmux

```bash
ln -sf ~/.dotfiles/tmux/tmux.conf ~/.tmux.conf
# install plugins (TPM), then link the patched tmux-colortag script
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
~/.tmux/plugins/tpm/bin/install_plugins
ln -sf ~/.dotfiles/tmux/colortag/name2color.py ~/.tmux/plugins/tmux-colortag/name2color.py
tmux source-file ~/.tmux.conf
```

`tmux/colortag/name2color.py` is a patched copy of the tmux-colortag script: 8-color palette, color by window index, and `--cycle` (`prefix y` next color, `prefix Y` previous). A plugin update (`prefix U`) may replace the link; re-run the last `ln -sf` line if colors go back to the old palette.
