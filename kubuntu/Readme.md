## Restore — after reinstalling Kubuntu

```bash
git clone <your-repo> ~/dotfiles

# ZSH
cp ~/dotfiles/kubuntu/zsh/.zshrc ~/
cp ~/dotfiles/kubuntu/zsh/.zshenv ~/          # if exists

# KDE
cp ~/dotfiles/kubuntu/kde/* ~/.config/

# Restart Plasma to apply
plasmashell --replace &
```
