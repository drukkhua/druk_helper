#!/usr/bin/env python3
"""
Улучшение системы для корректного определения цен на премиальные отделки
"""

import re
from typing import Dict, List, Optional


class PremiumPricingDetector:
    """Детектор премиальных отделок в запросах пользователей"""

    def __init__(self):
        # Ключевые слова премиальных материалов и отделок
        self.premium_keywords = {
            "materials": {
                "ukr": [
                    "чорний картон",
                    "чорному картоні",
                    "черный картон",
                    "премиум картон",
                    "дизайнерський картон",
                    "металізований",
                    "перламутровий",
                ],
                "rus": [
                    "черный картон",
                    "черном картоне",
                    "премиум картон",
                    "дизайнерский картон",
                    "металлизированный",
                    "перламутровый",
                ],
            },
            "finishes": {
                "ukr": [
                    "каширування",
                    "каширован",
                    "ламінування",
                    "фольгування",
                    "тиснення",
                    "лак",
                    "спот лак",
                    "soft touch",
                ],
                "rus": [
                    "каширование",
                    "кашированные",
                    "ламинирование",
                    "фольгирование",
                    "тиснение",
                    "лак",
                    "спот лак",
                    "софт тач",
                ],
            },
            "premium_features": {
                "ukr": ["закруглені кути", "вирубка", "конгрев", "шовкографія"],
                "rus": ["закругленные углы", "вырубка", "конгрев", "шелкография"],
            },
        }

        # Множители цен для разных типов премиальной отделки
        self.price_multipliers = {
            "black_cardboard": 1.3,  # +30%
            "lamination": 1.2,  # +20%
            "foiling": 1.8,  # +80%
            "spot_uv": 1.4,  # +40%
            "die_cutting": 1.5,  # +50%
            "soft_touch": 1.6,  # +60%
            "premium_complex": 4.5,  # Комплексные премиальные решения
            "luxury_materials": 5.0,  # Люксовые материалы
        }

        # Стратегии представления цен в зависимости от множителя
        self.pricing_strategies = {
            "moderate": {"range": (1.0, 1.5), "approach": "direct_pricing"},
            "premium": {"range": (1.5, 2.5), "approach": "exclusive_segment"},
            "luxury": {"range": (2.5, float("inf")), "approach": "vip_class"},
        }

    def detect_premium_features(self, query: str, language: str = "ukr") -> Dict:
        """
        Определяет премиальные особенности в запросе

        Returns:
            Dict с информацией о найденных премиальных особенностях
        """
        query_lower = query.lower()
        detected_features = []
        estimated_multiplier = 1.0

        # Проверяем материалы
        for keyword in self.premium_keywords["materials"][language]:
            if keyword.lower() in query_lower:
                # Определяем тип материала для правильного множителя
                if "чорний картон" in keyword.lower() or "черный картон" in keyword.lower():
                    multiplier = self.price_multipliers.get("black_cardboard", 1.3)
                elif (
                    "премиум" in keyword.lower()
                    or "дизайнерський" in keyword.lower()
                    or "дизайнерский" in keyword.lower()
                ):
                    multiplier = self.price_multipliers.get("premium_complex", 4.5)
                elif (
                    "металізований" in keyword.lower()
                    or "металлизированный" in keyword.lower()
                    or "перламутровий" in keyword.lower()
                    or "перламутровый" in keyword.lower()
                ):
                    multiplier = self.price_multipliers.get("luxury_materials", 5.0)
                else:
                    multiplier = self.price_multipliers.get("black_cardboard", 1.3)

                detected_features.append(
                    {
                        "type": "material",
                        "feature": keyword,
                        "multiplier": multiplier,
                    }
                )
                estimated_multiplier = max(estimated_multiplier, multiplier)

        # Проверяем отделки
        for keyword in self.premium_keywords["finishes"][language]:
            if keyword.lower() in query_lower:
                feature_type = self._map_keyword_to_feature(keyword)
                multiplier = self.price_multipliers.get(feature_type, 1.4)
                detected_features.append(
                    {"type": "finish", "feature": keyword, "multiplier": multiplier}
                )
                estimated_multiplier = max(estimated_multiplier, multiplier)

        # Проверяем дополнительные особенности
        for keyword in self.premium_keywords["premium_features"][language]:
            if keyword.lower() in query_lower:
                detected_features.append({"type": "feature", "feature": keyword, "multiplier": 1.4})
                estimated_multiplier = max(estimated_multiplier, 1.4)

        # Проверяем комбинации премиальных особенностей для увеличения множителя
        if len(detected_features) >= 2:
            # Если есть 2+ премиальные особенности, увеличиваем множитель
            if estimated_multiplier < 2.5:
                estimated_multiplier = min(4.5, estimated_multiplier * len(detected_features) * 0.8)

        return {
            "is_premium": len(detected_features) > 0,
            "features": detected_features,
            "estimated_multiplier": estimated_multiplier,
            "confidence": self._calculate_confidence(detected_features, query_lower),
        }

    def _map_keyword_to_feature(self, keyword: str) -> str:
        """Сопоставляет ключевое слово с типом отделки"""
        keyword_lower = keyword.lower()

        if any(word in keyword_lower for word in ["каширован", "каширування"]):
            return "lamination"
        elif any(word in keyword_lower for word in ["фольг", "foil"]):
            return "foiling"
        elif any(word in keyword_lower for word in ["лак", "uv"]):
            return "spot_uv"
        elif any(word in keyword_lower for word in ["soft", "софт"]):
            return "soft_touch"
        elif any(word in keyword_lower for word in ["вирубка", "вырубка"]):
            return "die_cutting"
        else:
            return "premium_finish"

    def _calculate_confidence(self, features: List[Dict], query: str) -> float:
        """Рассчитывает уверенность в определении премиальности"""
        if not features:
            return 0.0

        base_confidence = min(0.9, len(features) * 0.3 + 0.3)

        # Повышаем уверенность если есть прямые упоминания цены
        if any(word in query for word in ["цена", "ціна", "стоит", "коштує"]):
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _get_pricing_strategy(self, multiplier: float) -> str:
        """Определяет стратегию представления цены на основе множителя"""
        for strategy_name, strategy_data in self.pricing_strategies.items():
            min_range, max_range = strategy_data["range"]
            if min_range <= multiplier < max_range:
                return strategy_data["approach"]
        return "vip_class"  # По умолчанию для очень высоких цен

    def generate_premium_pricing_note(self, detection_result: Dict, language: str = "ukr") -> str:
        """Генерирует примечание о премиальном ценообразовании с психологически правильной подачей"""
        if not detection_result["is_premium"]:
            return ""

        features_list = [f["feature"] for f in detection_result["features"]]
        multiplier = detection_result["estimated_multiplier"]
        strategy = self._get_pricing_strategy(multiplier)

        if language == "ukr":
            return self._generate_ukr_pricing_note(features_list, multiplier, strategy)
        else:
            return self._generate_rus_pricing_note(features_list, multiplier, strategy)

    def _generate_ukr_pricing_note(
        self, features_list: List[str], multiplier: float, strategy: str
    ) -> str:
        """Генерирует украинскую версию примечания о ценах"""
        features_text = ", ".join(features_list)

        if strategy == "direct_pricing":
            # Для умеренного повышения (до 50%) - прямые цены
            base_price_96 = int(158 * multiplier)
            base_price_1000 = int(920 * multiplier)

            return f"""
✨ Преміальні візитки з особливостями: {features_text}

💰 Орієнтовні ціни з вашими покращеннями:
• 96 шт — від {base_price_96} грн
• 1000 шт — від {base_price_1000} грн

📞 Для точного розрахунку зв'яжіться з менеджером, оскільки фінальна ціна залежить від конкретних параметрів.

💡 Порада від Олени: Преміальні візитки створюють WOW-ефект і надовго запам'ятовуються клієнтам!"""

        elif strategy == "exclusive_segment":
            # Для премиальных цен (50-150%) - акцент на эксклюзивность
            return f"""
🎖️ Ексклюзивні візитки преміум-сегменту з особливостями: {features_text}

💎 Ціноутворення для преміум-сегменту:
• Це продукція вищої цінової категорії
• Ціна формується індивідуально залежно від складності
• Орієнтир: у 2-3 рази вище стандартних візиток

📞 Персональна консультація з менеджером допоможе підібрати оптимальне рішення для вашого бюджету.

🌟 Чому це варто інвестицій: Преміальні візитки — це не просто контакт, а перше враження, яке формує статус і довіру до вашого бренду."""

        else:  # vip_class
            # Для очень высоких цен (150%+) - VIP-класс и ценность
            per_piece_price = int((158 * multiplier) / 96)

            return f"""
👑 VIP-клас візиток з ексклюзивними особливостями: {features_text}

💎 Індивідуальне ціноутворення для VIP-продукції:
• Орієнтовна вартість: від {per_piece_price} грн за візитку
• Це авторська робота з унікальними матеріалами
• Термін виготовлення: 7-10 робочих днів

🎯 Персональний менеджер розрахує оптимальне рішення під ваш проєкт і бюджет.

🚀 Ефект від інвестицій: VIP-візитки перетворюють звичайне знайомство в запам'ятовуючий досвід, підвищують сприйняття статусу та професіоналізму у рази."""

    def _generate_rus_pricing_note(
        self, features_list: List[str], multiplier: float, strategy: str
    ) -> str:
        """Генерирует русскую версию примечания о ценах"""
        features_text = ", ".join(features_list)

        if strategy == "direct_pricing":
            # Для умеренного повышения (до 50%) - прямые цены
            base_price_96 = int(158 * multiplier)
            base_price_1000 = int(920 * multiplier)

            return f"""
✨ Премиальные визитки с особенностями: {features_text}

💰 Ориентировочные цены с вашими улучшениями:
• 96 шт — от {base_price_96} грн
• 1000 шт — от {base_price_1000} грн

📞 Для точного расчета свяжитесь с менеджером, поскольку финальная цена зависит от конкретных параметров.

💡 Совет от Олены: Премиальные визитки создают WOW-эффект и надолго запоминаются клиентам!"""

        elif strategy == "exclusive_segment":
            # Для премиальных цен (50-150%) - акцент на эксклюзивность
            return f"""
🎖️ Эксклюзивные визитки премиум-сегмента с особенностями: {features_text}

💎 Ценообразование для премиум-сегмента:
• Это продукция высшей ценовой категории
• Цена формируется индивидуально в зависимости от сложности
• Ориентир: в 2-3 раза выше стандартных визиток

📞 Персональная консультация с менеджером поможет подобрать оптимальное решение для вашего бюджета.

🌟 Почему это стоит инвестиций: Премиальные визитки — это не просто контакт, а первое впечатление, которое формирует статус и доверие к вашему бренду."""

        else:  # vip_class
            # Для очень высоких цен (150%+) - VIP-класс и ценность
            per_piece_price = int((158 * multiplier) / 96)

            return f"""
👑 VIP-класс визиток с эксклюзивными особенностями: {features_text}

💎 Индивидуальное ценообразование для VIP-продукции:
• Ориентировочная стоимость: от {per_piece_price} грн за визитку
• Это авторская работа с уникальными материалами
• Срок изготовления: 7-10 рабочих дней

🎯 Персональный менеджер рассчитает оптимальное решение под ваш проект и бюджет.

🚀 Эффект от инвестиций: VIP-визитки превращают обычное знакомство в запоминающийся опыт, повышают восприятие статуса и профессионализма в разы."""


def enhance_ai_response_with_premium_pricing(
    original_response: str, user_query: str, language: str = "ukr"
) -> str:
    """
    Улучшает ответ AI с учетом премиального ценообразования

    Args:
        original_response: Оригинальный ответ от AI
        user_query: Запрос пользователя
        language: Язык ответа

    Returns:
        Улучшенный ответ с корректной информацией о ценах
    """
    detector = PremiumPricingDetector()
    detection = detector.detect_premium_features(user_query, language)

    if not detection["is_premium"]:
        return original_response

    # Генерируем примечание о премиальном ценообразовании
    premium_note = detector.generate_premium_pricing_note(detection, language)

    # Если в оригинальном ответе есть стандартные цены, добавляем предупреждение
    if any(price in original_response for price in ["158 грн", "920 грн"]):
        if language == "ukr":
            warning = "\n\n⚠️ Увага: Вказані ціни для стандартних візиток. Для преміальних матеріалів ціни будуть вищими."
        else:
            warning = "\n\n⚠️ Внимание: Указанные цены для стандартных визиток. Для премиальных материалов цены будут выше."

        # Вставляем предупреждение перед контактной информацией
        if (
            "зв'яжіться з менеджером" in original_response
            or "свяжитесь с менеджером" in original_response
        ):
            parts = original_response.split(
                "зв'яжіться з менеджером" if language == "ukr" else "свяжитесь с менеджером"
            )
            enhanced_response = (
                parts[0]
                + warning
                + premium_note
                + "\n\nЗв'яжіться з менеджером"
                + "".join(parts[1:])
                if language == "ukr"
                else parts[0]
                + warning
                + premium_note
                + "\n\nСвяжитесь с менеджером"
                + "".join(parts[1:])
            )
        else:
            enhanced_response = original_response + warning + premium_note
    else:
        enhanced_response = original_response + premium_note

    return enhanced_response


# Функция для интеграции в Enhanced AI Service
def integrate_premium_pricing_detection():
    """
    Пример интеграции в Enhanced AI Service
    """

    example_usage = """
    # В enhanced_ai_service.py в методе _process_with_enhanced_openai или _process_with_enhanced_mock

    # После получения ответа от OpenAI:
    original_answer = response.choices[0].message.content.strip()

    # Улучшаем ответ с учетом премиального ценообразования
    enhanced_answer = enhance_ai_response_with_premium_pricing(
        original_answer,
        user_query,
        language
    )

    return {
        "answer": enhanced_answer,
        "confidence": confidence,
        "source": "enhanced_openai_with_premium_pricing"
    }
    """

    return example_usage


if __name__ == "__main__":
    # Тестирование системы
    detector = PremiumPricingDetector()

    test_queries = [
        "Скільки коштують візитки на чорному картоні?",
        "Хочу візитки з кашируванням",
        "Можна зробити візитки з фольгуванням?",
        "Звичайні візитки, скільки коштують?",
        "Візитки з soft touch покриттям",
    ]

    for query in test_queries:
        print(f"\n🔍 Запрос: {query}")
        result = detector.detect_premium_features(query, "ukr")
        print(f"   Премиальный: {result['is_premium']}")
        print(f"   Множитель: {result['estimated_multiplier']:.1f}x")
        print(f"   Особенности: {[f['feature'] for f in result['features']]}")
