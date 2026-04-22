import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'uz' | 'en' | 'ru'

interface I18nState {
  language: Language
  setLanguage: (lang: Language) => void
}

export const useI18nStore = create<I18nState>()(
  persist(
    (set) => ({
      language: 'uz',
      setLanguage: (language) => set({ language }),
    }),
    {
      name: 'artificial-teacher-lang',
    }
  )
)

type TranslationDict = Record<string, Record<Language, string>>

const dict: TranslationDict = {
  // Navigation & Common
  back: { uz: 'Orqaga', en: 'Back', ru: 'Назад' },
  loading: { uz: 'Yuklanmoqda...', en: 'Loading...', ru: 'Загрузка...' },
  error: { uz: 'Xatolik yuz berdi', en: 'An error occurred', ru: 'Произошла ошибка' },
  retry: { uz: 'Qayta urinish', en: 'Retry', ru: 'Повторить' },
  
  // Difficulties
  easy: { uz: 'Oson', en: 'Easy', ru: 'Легкий' },
  medium: { uz: "O'rta", en: 'Medium', ru: 'Средний' },
  hard: { uz: 'Qiyin', en: 'Hard', ru: 'Сложный' },
  
  // Number Game
  num_title: { uz: 'Raqam Topish', en: 'Number Guess', ru: 'Угадай число' },
  num_desc: { uz: 'Daraja tanlang', en: 'Select difficulty', ru: 'Выберите сложность' },
  num_start: { uz: "O'yinni boshlash", en: 'Start Game', ru: 'Начать игру' },
  num_guess: { uz: 'Raqam toping', en: 'Guess the number', ru: 'Угадайте число' },
  num_range: { uz: 'orasidan', en: 'between', ru: 'в диапазоне' },
  num_attempts: { uz: 'ta urinish', en: 'attempts', ru: 'попыток' },
  num_left: { uz: 'ta urinish qoldi', en: 'attempts left', ru: 'осталось попыток' },
  num_correct: { uz: "🎯 To'g'ri!", en: '🎯 Correct!', ru: '🎯 Правильно!' },
  num_close_up: { uz: '🔥 Juda yaqin! Kattaroq', en: '🔥 Very close! Higher', ru: '🔥 Очень близко! Больше' },
  num_close_down: { uz: '🔥 Juda yaqin! Kichikroq', en: '🔥 Very close! Lower', ru: '🔥 Очень близко! Меньше' },
  num_warm_up: { uz: '♨️ Iliq! Kattaroq', en: '♨️ Warm! Higher', ru: '♨️ Тепло! Больше' },
  num_warm_down: { uz: '♨️ Iliq! Kichikroq', en: '♨️ Warm! Lower', ru: '♨️ Тепло! Меньше' },
  num_cold_up: { uz: '❄️ Sovuq! Kattaroq', en: '❄️ Cold! Higher', ru: '❄️ Холодно! Больше' },
  num_cold_down: { uz: '❄️ Sovuq! Kichikroq', en: '❄️ Cold! Lower', ru: '❄️ Холодно! Меньше' },
  num_win: { uz: "To'g'ri topdingiz!", en: 'You guessed it!', ru: 'Вы угадали!' },
  num_lose: { uz: "Afsus, yutqazdingiz!", en: 'Game Over!', ru: 'Игра окончена!' },
  num_answer_was: { uz: 'Javob: {x} edi', en: 'Answer was: {x}', ru: 'Ответ был: {x}' },
  num_new: { uz: 'Yangi raqam', en: 'New Number', ru: 'Новое число' },
  num_setup: { uz: 'Sozlashga', en: 'To Setup', ru: 'К настройкам' },
  total_score: { uz: 'Jami ball', en: 'Total score', ru: 'Общий счет' },
  score_plus: { uz: '+{x} ball!', en: '+{x} points!', ru: '+{x} очков!' },

  // Math Game
  math_title: { uz: 'Tez Hisob', en: 'Fast Math', ru: 'Быстрая Математика' },
  math_questions: { uz: 'savol', en: 'questions', ru: 'вопросов' },
  math_start: { uz: 'Boshlash', en: 'Start', ru: 'Начать' },
  math_calc: { uz: 'Hisoblang', en: 'Calculate', ru: 'Посчитайте' },
  math_right: { uz: "To'g'ri!", en: 'Correct!', ru: 'Правильно!' },
  math_wrong: { uz: "Noto'g'ri! Javob: {x}", en: 'Wrong! Answer: {x}', ru: 'Неверно! Ответ: {x}' },
  math_awesome: { uz: 'Ajoyib!', en: 'Awesome!', ru: 'Отлично!' },
  math_good: { uz: "Zo'r!", en: 'Great!', ru: 'Хорошо!' },
  math_bad: { uz: 'Mashq qilish kerak!', en: 'Need practice!', ru: 'Нужна практика!' },
  math_score: { uz: 'Ball', en: 'Score', ru: 'Очки' },
  math_correct_count: { uz: "To'g'ri", en: 'Correct', ru: 'Верно' },
  math_accuracy: { uz: 'Aniqlik', en: 'Accuracy', ru: 'Точность' },
  math_again: { uz: 'Qayta', en: 'Again', ru: 'Снова' },
  
  // IQ Test
  iq_title: { uz: 'IQ Test', en: 'IQ Test', ru: 'IQ Тест' },
  iq_desc: { uz: 'Mantiqiy fikrlash darajangizni sinab ko\'ring.', en: 'Test your logical thinking skills.', ru: 'Проверьте свое логическое мышление.' },
  iq_submit_err: { uz: 'Natijani yuborishda xatolik yuz berdi.', en: 'Error submitting result.', ru: 'Ошибка при отправке результата.' },
  iq_result: { uz: 'IQ Test Natijasi', en: 'IQ Test Result', ru: 'Результат IQ Теста' },
  iq_new_best: { uz: '🌟 Yangi rekord!', en: '🌟 New record!', ru: '🌟 Новый рекорд!' },
  iq_desc_res: { uz: 'Sizning mantiqiy fikrlash darajangiz yuqoridagi ko\'rsatkich bilan baholandi. Bu natija profil statistikasiga saqlandi.', en: 'Your logical thinking level was evaluated with the score above. This result has been saved to your profile statistics.', ru: 'Ваш уровень логического мышления был оценен вышеуказанным показателем. Этот результат сохранен в статистике профиля.' },
  iq_back_home: { uz: 'Bosh sahifaga qaytish', en: 'Back to Home', ru: 'Вернуться на главную' },
  iq_no_questions: { uz: 'Savollar topilmadi.', en: 'No questions found.', ru: 'Вопросы не найдены.' },
  iq_question: { uz: 'Savol', en: 'Question', ru: 'Вопрос' },
  iq_time: { uz: 'Vaqt', en: 'Time', ru: 'Время' },
  iq_prev: { uz: 'Oldingi', en: 'Previous', ru: 'Предыдущий' },
  iq_next: { uz: 'Keyingi', en: 'Next', ru: 'Следующий' },
  iq_finish: { uz: 'Yakunlash', en: 'Finish', ru: 'Завершить' },
  
  // Library
  lib_title: { uz: 'Kutubxona', en: 'Library', ru: 'Библиотека' },
  lib_desc: { uz: 'Ingliz tilidagi kitoblar va matnlar', en: 'English books and texts', ru: 'Книги и тексты на английском' },
  lib_books: { uz: 'Kitoblar', en: 'Books', ru: 'Книги' },
  lib_facts: { uz: 'Faktlar', en: 'Facts', ru: 'Факты' },
  lib_quiz: { uz: 'Zakovat', en: 'Quiz', ru: 'Викторина' },
  lib_search: { uz: '{x}dan izlash...', en: 'Search in {x}...', ru: 'Поиск в {x}...' },
  lib_not_found: { uz: 'Hech narsa topilmadi 😔', en: 'Nothing found 😔', ru: 'Ничего не найдено 😔' },
  lib_show_answer: { uz: 'Javobni ko\'rish', en: 'Show answer', ru: 'Показать ответ' },
  lib_year: { uz: 'Yil', en: 'Year', ru: 'Год' },
  lib_region: { uz: 'Hudud', en: 'Region', ru: 'Регион' },
}

export function useTranslation() {
  const { language } = useI18nStore()
  
  return (key: string, params?: Record<string, string | number>) => {
    let str = dict[key]?.[language] || key
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        str = str.replace(`{${k}}`, String(v))
      })
    }
    return str
  }
}
