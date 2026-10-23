"""
Management command: seed_data
Populates the database with realistic demo data.
Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # wipe then re-seed
"""
import random
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from products.models import Product, Review, Trend


PRODUCTS = [
    {
        "name": "Sony WH-1000XM5 Wireless Headphones",
        "description": (
            "Industry-leading noise cancellation with exceptional sound quality. "
            "Used for 6 months, no scratches, original packaging included. "
            "Comes with all accessories: carrying case, cables, and ear cushions. "
            "Battery life still at 100% capacity. A must-have for audiophiles."
        ),
        "price": 249,
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=400&fit=crop",
    },
    {
        "name": "Nike Air Jordan 1 Retro High OG",
        "description": (
            "Iconic Chicago colorway, deadstock condition (DS). Size US 10 / EU 44. "
            "Never worn, stored in climate-controlled environment. "
            "Receipt available, purchased directly from Nike SNKRS. "
            "Box is pristine with zero yellowing on the midsole."
        ),
        "price": 320,
        "category": "Sneakers",
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=400&fit=crop",
    },
    {
        "name": "Apple MacBook Pro 14\" M3 Pro",
        "description": (
            "MacBook Pro 14-inch with M3 Pro chip, 18GB RAM, 512GB SSD in Space Black. "
            "8 months old, AppleCare+ until 2026. Used lightly for software development. "
            "Screen is flawless, keyboard pristine. Selling to upgrade to M4 Max. "
            "Original charger and box included."
        ),
        "price": 1750,
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1496181891893-04af56ab55c4?w=600&h=400&fit=crop",
    },
    {
        "name": "Rolex Submariner Date 116610LN",
        "description": (
            "Rolex Submariner Date in Oystersteel with black dial and bezel. "
            "Full set: box, papers, hang tags. Purchased 2021, serviced 2023. "
            "Worn casually, no dive history. Ceramic bezel shows minimal hairlines. "
            "Bracelet has light stretching, easily tightened by watchmaker."
        ),
        "price": 9500,
        "category": "Watches",
        "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=400&fit=crop",
    },
    {
        "name": "Supreme Box Logo Hoodie FW23",
        "description": (
            "Supreme FW23 Box Logo Hoodie in Forest Green, size Large. "
            "Brand new with tags, purchased from Supreme online drop. "
            "100% authentic, verified by StockX. "
            "Sold out everywhere — rare grail piece for collectors."
        ),
        "price": 450,
        "category": "Fashion",
        "image": "https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600&h=400&fit=crop",
    },
    {
        "name": "PlayStation 5 Disc Edition Bundle",
        "description": (
            "PS5 Disc Edition console with two DualSense controllers and 5 games. "
            "Purchased at launch, lightly used for gaming sessions. "
            "Works perfectly, quiet fan. Comes with HDMI 2.1 cable and all original accessories. "
            "Games included: God of War Ragnarök, Spider-Man 2, Horizon FW, GT7, Elden Ring."
        ),
        "price": 520,
        "category": "Gaming",
        "image": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=600&h=400&fit=crop",
    },
    {
        "name": "Leica M6 TTL 0.85 35mm Film Camera",
        "description": (
            "Leica M6 TTL in classic black chrome finish. "
            "Light meter fully functional, shutter speeds accurate across all settings. "
            "Viewfinder is crystal clear with no haze. "
            "Comes with Voigtländer 35mm f/1.4 Nokton lens and original strap."
        ),
        "price": 2200,
        "category": "Collectibles",
        "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&h=400&fit=crop",
    },
    {
        "name": "Ray-Ban Wayfarer RB2140 Classic",
        "description": (
            "Original Ray-Ban Wayfarer in classic black frames with G-15 lenses. "
            "Barely used, kept in case at all times. No scratches on lenses. "
            "Original case and cleaning cloth. Purchased from authorized retailer. "
            "Timeless piece that pairs with any outfit."
        ),
        "price": 85,
        "category": "Fashion",
        "image": "https://images.unsplash.com/photo-1511499767150-a7a1371bf12c?w=600&h=400&fit=crop",
    },
    {
        "name": "Louis Vuitton Monogram Backpack",
        "description": (
            "Louis Vuitton Monogram Canvas Backpack in excellent condition. "
            "Purchased at LV flagship store, receipt available. "
            "Interior is clean, zipper functions smoothly, vachetta has developed beautiful patina. "
            "Light wear on corners consistent with age. Authentic with date code."
        ),
        "price": 1100,
        "category": "Fashion",
        "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=400&fit=crop",
    },
    {
        "name": "Vintage Vinyl Record Collection (50 LPs)",
        "description": (
            "Carefully curated collection of 50 vinyl LPs spanning jazz, soul, and classic rock. "
            "Highlights: Miles Davis Kind of Blue, Coltrane A Love Supreme, Marvin Gaye What's Going On. "
            "All records graded VG+ to NM. Stored in anti-static sleeves. "
            "Custom wooden crate included. Selling to fund studio renovations."
        ),
        "price": 380,
        "category": "Collectibles",
        "image": "https://images.unsplash.com/photo-1535712593684-0efd522bc77c?w=600&h=400&fit=crop",
    },
    {
        "name": "Adidas Yeezy Boost 350 V2 Zebra",
        "description": (
            "Adidas Yeezy 350 V2 in the iconic Zebra (CP9654) colorway, size US 9.5. "
            "Worn twice, virtually deadstock. No sole yellowing or separation. "
            "Original box and receipt from Adidas.com included. "
            "StockX authentication badge attached. Classic investment piece."
        ),
        "price": 280,
        "category": "Sneakers",
        "image": "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=600&h=400&fit=crop",
    },
    {
        "name": "Dyson V15 Detect Absolute Vacuum",
        "description": (
            "Dyson V15 Detect with full accessory kit: laser slim fluffy head, torque drive, "
            "crevice tool, and 3 attachments. 18 months old, serviced and cleaned. "
            "All attachments included. Battery holds full charge. "
            "Selling because we moved and have hardwood floors only."
        ),
        "price": 380,
        "category": "Home & Lifestyle",
        "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=400&fit=crop",
    },
]


REVIEWS = [
    # Sony headphones reviews
    ("TechFan_Marco", 5, "Absolutely incredible noise cancellation. Best headphones I've ever owned."),
    ("AudiophileJen", 5, "Sound quality is out of this world. Seller was great, fast shipping."),
    ("MusicLover99", 5, "These arrived in perfect condition exactly as described. 10/10 would buy again."),
    ("DJMike_Berlin", 4, "Great headphones, slight wear on earcups not mentioned but still happy."),
    ("WorkFromHome_Lisa", 5, "Game changer for remote work. Zero background noise. Highly recommend."),

    # Jordan reviews
    ("SneakerHead_NYC", 5, "DS as advertised. Legit checked instantly. These are the real deal."),
    ("KicksCollector_EU", 5, "Packaging was immaculate, shoes are stunning. A grail item finally in my collection."),
    ("JordanFan_Paris", 5, "Seller responded fast, shipped same day. Shoes are perfect. Five stars!"),
    ("StreetStyle_Alex", 4, "Beautiful pair. Box has a small dent but shoes are flawless."),
    ("RetroVibes_Sam", 5, "Worth every euro. Already got multiple compliments wearing them."),

    # MacBook reviews
    ("DevLife_Tom", 5, "M3 Pro is a beast. Exactly as described, battery health at 97%. Loving it."),
    ("DesignerAnna", 5, "Fast shipping, well packed. The screen is gorgeous, no dead pixels."),
    ("FreelancerMax", 5, "Saved me 800€ vs new. Works like brand new. Highly recommended seller."),
    ("StartupFounder_K", 4, "Great laptop, minor smudge on bottom I had to wipe off but works perfectly."),
    ("CodeMonkey_Reza", 5, "This is the best laptop I've ever used. Seller was honest and professional."),

    # Rolex reviews
    ("WatchEnthusiast_CH", 5, "Pristine Sub, full set. One of the cleanest references I've added to the collection."),
    ("HorologyFan_DE", 5, "Seller provided all documentation. Watch runs spot on. Top-tier transaction."),
    ("InvestorWatch_HK", 5, "Market timing was perfect. Arrived impeccably packed with white gloves care."),

    # Supreme reviews
    ("Streetwear_Tokyo", 5, "100% legit, verified on GOAT before shipping. The colorway is fire."),
    ("HypeCollector_LA", 5, "Exactly what the hype is about. Fits perfectly, fabric is premium."),
    ("FashionForward_EU", 5, "Rare find at a fair price. Seller was transparent and quick."),
    ("BoxLogoFiend_NY", 4, "Love the hoodie, one small loose thread but quality is still top-notch."),

    # PS5 reviews
    ("GamerGuy_Berlin", 5, "PS5 runs perfectly quiet, games were a bonus. Best purchase of the year."),
    ("ConsoleFan_Madrid", 5, "Seller packed it incredibly well. Everything works. Spider-Man 2 is incredible."),
    ("RetroGamer_Vik", 5, "Tested everything before listing, all accurate. Fast shipping. 10/10."),
    ("GameNight_Sophie", 4, "Console is great, one controller has slight stick drift but totally manageable."),

    # Leica reviews
    ("FilmPhoto_Studio", 5, "The M6 is a legend and this one is in incredible shape. Seller is an expert."),
    ("StreetPhotog_Kai", 5, "Meter is precise, shutter is buttery smooth. The Voigt lens is a gem. Perfect deal."),
    ("AnalogLife_Flo", 5, "Shot my first roll through it — results are stunning. Honest seller."),

    # General reviews
    ("BargainHunter_EU", 5, "Great condition, accurate description, fast shipping. Solid reseller."),
    ("Trustworthy_Buyer", 5, "Fifth time buying through ResaleAI. Never disappointed. Quality platform."),
    ("FirstTimeBuyer_Jo", 5, "Was nervous about buying second-hand but the AI pricing made it easy to trust."),
    ("CollectorMindset", 5, "Pristine item, arrived two days early. Seller went above and beyond."),
    ("LuxuryResale_Pro", 5, "Everything about this transaction was flawless. The AI estimate was spot on!"),
]


TRENDS = [
    {
        "name": "Vintage Film Photography",
        "category": "Collectibles",
        "popularity_score": 94,
        "description": (
            "Analog cameras and film gear are experiencing a massive resurgence. "
            "Leica, Contax, and Nikon F-series models are commanding record prices. "
            "Gen Z buyers are driving demand to all-time highs."
        ),
    },
    {
        "name": "Nike x Off-White Collaborations",
        "category": "Sneakers",
        "popularity_score": 91,
        "description": (
            "Virgil Abloh's posthumous releases and archival Off-White collaborations "
            "continue to appreciate rapidly. The 'The 10' series shows no signs of cooling."
        ),
    },
    {
        "name": "Apple Silicon Laptops",
        "category": "Electronics",
        "popularity_score": 87,
        "description": (
            "Used MacBooks with M-series chips hold value exceptionally well. "
            "The gap between new and used pricing is narrowing as demand outstrips supply "
            "in the secondary market."
        ),
    },
    {
        "name": "Swiss Entry-Level Luxury Watches",
        "category": "Watches",
        "popularity_score": 83,
        "description": (
            "Tudor, TAG Heuer, and Longines are seeing increased interest as buyers look "
            "for gateway pieces into Swiss watchmaking. The Tudor Black Bay is the standout."
        ),
    },
    {
        "name": "Streetwear Archive Pieces",
        "category": "Fashion",
        "popularity_score": 79,
        "description": (
            "Early 2010s Supreme, BAPE, and Palace items are trading at 5–10x original retail. "
            "Condition and authenticity documentation are key value drivers."
        ),
    },
    {
        "name": "Next-Gen Gaming Consoles",
        "category": "Gaming",
        "popularity_score": 74,
        "description": (
            "PS5 slim and Xbox Series X bundles continue to flip well. "
            "Limited edition console variants can yield 40–60% margins in secondary markets."
        ),
    },
    {
        "name": "Audiophile Headphones & DACs",
        "category": "Electronics",
        "popularity_score": 68,
        "description": (
            "Sony, Sennheiser, and Audeze flagship headphones retain 70–80% of retail value "
            "used. The work-from-home era permanently elevated demand for premium audio."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed the database with demo products, reviews, and trends."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Ukázková data nelze seedovat při DEBUG=False.")

        if options["flush"]:
            self.stdout.write("Flushing existing data…")
            Review.objects.all().delete()
            Product.objects.all().delete()
            Trend.objects.all().delete()

        # ── Trends ────────────────────────────────────────────────────────────
        self.stdout.write("Seeding trends…")
        for td in TRENDS:
            Trend.objects.get_or_create(
                name=td["name"],
                defaults={
                    "category": td["category"],
                    "popularity_score": td["popularity_score"],
                    "description": td["description"],
                },
            )

        # ── Products ──────────────────────────────────────────────────────────
        self.stdout.write("Seeding products…")
        created_products = []
        for pd in PRODUCTS:
            product, created = Product.objects.get_or_create(
                name=pd["name"],
                defaults={
                    "description": pd["description"],
                    "price": pd["price"],
                    "category": pd["category"],
                    "image": pd["image"],
                },
            )
            if created:
                created_products.append(product)
            self.stdout.write(f"  {'✓' if created else '–'} {product.name}")

        # ── Reviews ───────────────────────────────────────────────────────────
        self.stdout.write("Seeding reviews…")
        all_products = list(Product.objects.all())
        review_pool = list(REVIEWS)
        random.shuffle(review_pool)

        for i, (username, rating, comment) in enumerate(review_pool):
            target = all_products[i % len(all_products)]
            Review.objects.get_or_create(
                product=target,
                username=username,
                defaults={"rating": rating, "comment": comment},
            )

        # Additional bulk reviews for realistic counts
        extra_users = [
            "PlatformUser_A", "ResaleEnthusiast_B", "ValueHunter_C",
            "SmartShopper_D", "TrustReviewer_E", "HappyBuyer_F",
            "GoodDeal_G", "QualityFirst_H", "QuickShip_I", "PerfectItem_J",
        ]
        extra_comments = [
            "Exactly as described. Very happy with this purchase!",
            "Item arrived in perfect condition. Seller communicated well.",
            "Great value. The AI price estimate was accurate.",
            "Packaging was excellent. Item is in better condition than photos show.",
            "Quick dispatch, well wrapped. Would buy from this seller again.",
            "No complaints whatsoever. Smooth transaction from start to finish.",
            "Very pleased. Matched the listing description exactly.",
            "Five stars all around. Highly recommend this listing.",
            "Seller was responsive and professional. Item is wonderful.",
            "Arrived faster than expected. Pristine condition.",
        ]
        for product in all_products:
            for j in range(3):
                user = random.choice(extra_users) + str(random.randint(10, 99))
                rating = random.choices([5, 5, 5, 4, 3], weights=[60, 20, 10, 7, 3])[0]
                comment = random.choice(extra_comments)
                Review.objects.get_or_create(
                    product=product,
                    username=user,
                    defaults={"rating": rating, "comment": comment},
                )

        total_p = Product.objects.count()
        total_r = Review.objects.count()
        total_t = Trend.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seeding complete!\n"
            f"   Products : {total_p}\n"
            f"   Reviews  : {total_r}\n"
            f"   Trends   : {total_t}\n"
        ))
