/**
 * Главная страница — случайное отображение одного изображения
 * и навигация по кнопке «Tail-ent Showcase».
 */

// Добавляем класс тёмной темы для главной страницы
document.body.classList.add('theme-dark');

const allImgBlocks = document.querySelectorAll('.hero__img');
const randomIndex = Math.floor(Math.random() * allImgBlocks.length);
const randomBlock = allImgBlocks[randomIndex];
randomBlock.classList.add('is-visible');

document.addEventListener('DOMContentLoaded', function () {
    const showcaseButton = document.querySelector('.header__button-btn');
    if (showcaseButton) {
        showcaseButton.addEventListener('click', function () {
            window.location.href = '/upload';
        });
    }
});