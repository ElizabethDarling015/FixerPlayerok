# Как выпустить релиз

1. Обновите версию в `cardinal/__init__.py` (`__version__`) и допишите раздел в `CHANGELOG.md`.
2. Закоммитьте и запушьте `main`.
3. Тег и релиз на GitHub (нужен [gh](https://cli.github.com/) или веб-интерфейс Releases):

```bash
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0 --title "PlayerokCardinal v1.0.0" --notes-file CHANGELOG.md
```

GitHub сам приложит к релизу архивы исходников — их скачивания считает бейдж
`github/downloads/.../total` в README. Автообновление бота (`[updates]`) работает по ветке
`main` и от тегов не зависит.
