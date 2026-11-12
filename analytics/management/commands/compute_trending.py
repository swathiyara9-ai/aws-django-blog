from django.core.management.base import BaseCommand
from analytics.services import compute_trending_scores
from analytics.models import PostStats


class Command(BaseCommand):
    help = 'Recalculates views, likes, comments, and time-decayed trending scores for all published posts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Computing trending scores..."))
        
        updated_stats = compute_trending_scores()
        
        # Display leaderboard
        top_posts = PostStats.objects.select_related('post').order_by('-score')[:5]
        
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully computed trending scores for {len(updated_stats)} post(s)."))
        self.stdout.write("\n--- Current Top Trending Posts ---")
        
        if top_posts.exists():
            for rank, stat in enumerate(top_posts, start=1):
                self.stdout.write(
                    f"{rank}. [Score: {stat.score:.2f}] \"{stat.post.title}\" "
                    f"(Views: {stat.views}, Comments: {stat.comments}, Likes: {stat.likes})"
                )
        else:
            self.stdout.write("No published posts found.")

