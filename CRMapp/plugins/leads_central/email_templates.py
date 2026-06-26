# email_templates.py

DEFAULT_CONTACT_INFO = {
    '254': {'phone': '254-300-9800', 'form_url': 'https://form.jotform.com/250440244093145'},
    '361': {'phone': '361-210-8800', 'form_url': 'https://form.jotform.com/250377181864160'},
    '214': {'phone': '214-561-0000', 'form_url': 'https://form.jotform.com/250434921055148'},
    '713': {'phone': '713-425-6800', 'form_url': 'https://form.jotform.com/250940705903152'},
    '817': {'phone': '817-618-9400', 'form_url': 'https://form.jotform.com/251325918462156'},
    '512': {'phone': '512-887-5400', 'form_url': 'https://form.jotform.com/251326327969163'},
}

AGENT_REFERRAL_EMAIL = """
Hello,

At Connect My New Home, we make moving easier by helping new residents quickly connect their Water, Electricity, Internet, and Home Security—at no cost to them. Our service saves clients time, money, and hassle during one of the busiest moments in their lives.

Over the past 9 years, we’ve helped more than 6,000 customers get connected with essential home services. We currently operate physical locations in Killeen and Corpus Christi.

We’re looking to build long-term partnerships and want to prove ourselves to you. For every successful connection, we’ll pay you:
• $20 for each electricity setup
• $60 for each internet installation
• $100 for every security system we install

We’ve made it easy for you to refer your clients using a simple link you can text or email. The key is timing—we need to reach your clients before their move-in date since most people schedule utilities in advance.

Give us a trial run for a week or two. We’re confident your clients will thank you, and you’ll see a noticeable boost in your earnings.

Thank you for your time and consideration.

Sincerely,  
Chuck  
Connect My New Home
"""

def get_customer_pitch_email(category, area_code):
    data = DEFAULT_CONTACT_INFO.get(area_code)
    if not data:
        return "Contact us directly at connectmynewhome.com for your utility setup!"

    if category in ['Realtors', 'Property Management']:
        home_word = 'dream' if category == 'Realtors' else 'new'
        return f"""
We’re so excited to have helped you find your {home_word} home! 🏡✨

Now let’s make moving a little easier (and cheaper)!
Save time & money by setting up your electricity ⚡️, water 💧, internet 🌐, security 🛡️, and more—all with ONE simple call ☎️

Connect My New Home offers a FREE utility concierge service—fast and hassle-free ✅

Call {data['phone']} 📞 or fill out this short form: 👉 {data['form_url']} 📝

No fees ❌ No stress 😌 Just one call and done ✔️  
Thanks again for letting us be a part of your journey. We appreciate you! ❤️
"""

    elif category == 'Movers':
        return f"""
Thank You for Choosing Us! 🎉

We’re excited to help you with your move 🚚. Now, let us help you make the transition even smoother (and cheaper)!

🏠 Get Your New Home Ready in No Time 🏠

With just one phone call or click the link below 👉  
{data['form_url']} 📝

Connect My New Home handles your utilities—water, electricity, internet, home security, and more—completely FREE!

💵 Save time and money! 💵 Call: {data['phone']} ☎️

Thanks for trusting us with your move! We truly appreciate your business! 👍
"""

    else:
        return f"""
Thank you for choosing Connect My New Home! 🎉

Let us help you make moving easy by setting up your utilities—water, electricity, internet, home security, and more—quickly and completely FREE!

Call us at {data['phone']} 📞 or complete this short form: {data['form_url']} 📝

We appreciate your trust and look forward to assisting you! 👍
"""

def get_agent_referral_email():
    return AGENT_REFERRAL_EMAIL
