"""Диагностика get_deal для последней сделки."""
import asyncio
from playerokapi.account import Account
from cardinal.settings import load_main_settings

async def main():
    settings = load_main_settings()
    account = Account(
        cookies=settings.playerok.cookies,
        user_agent=settings.playerok.user_agent,
        proxy=settings.playerok.proxy,
    )
    
    print("Авторизуемся...")
    await asyncio.to_thread(account.get)
    
    print("Получаем последнюю сделку...")
    deals_page = await asyncio.to_thread(account.get_deals, count=1)
    if not deals_page or not deals_page.deals:
        print("❌ Нет сделок")
        return
    
    deal = deals_page.deals[0]
    print(f"\n=== Сделка из get_deals() ===")
    print(f"ID: {deal.id}")
    print(f"Лот: {deal.item.name if deal.item else 'None'}")
    print(f"Покупатель: {deal.user.username if deal.user else 'None'}")
    print(f"Статус: {deal.raw_status.name if deal.raw_status else 'None'}")
    print(f"chat: {deal.chat}")
    print(f"item.game: {deal.item.game if deal.item else 'None'}")
    print(f"item.category: {deal.item.category if deal.item else 'None'}")
    
    print(f"\n=== Вызываем get_deal({deal.id}) ===")
    try:
        full_deal = await asyncio.to_thread(account.get_deal, deal.id)
        print(f"Тип результата: {type(full_deal)}")
        if full_deal is None:
            print("❌ get_deal вернул None")
            return
        
        print(f"\n=== Данные из get_deal() ===")
        print(f"ID: {full_deal.id}")
        print(f"chat: {full_deal.chat}")
        if full_deal.chat:
            print(f"chat.id: {full_deal.chat.id}")
        print(f"item: {full_deal.item}")
        if full_deal.item:
            print(f"item.name: {full_deal.item.name}")
            print(f"item.game: {full_deal.item.game}")
            if full_deal.item.game:
                print(f"item.game.name: {full_deal.item.game.name}")
            print(f"item.category: {full_deal.item.category}")
            if full_deal.item.category:
                print(f"item.category.name: {full_deal.item.category.name}")
        
        print("\n✅ Всё работает — данные получены")
    except Exception as exc:
        print(f"❌ get_deal упал с ошибкой: {exc}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())