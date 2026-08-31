from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from authentication.models import ActivityLog
from cards.models import Card


class RejectedCardDeleteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='TestPass123'
        )
        self.card = Card.objects.create(
            user=self.user,
            card_no='CARD-DELETE-001',
            iqama_no='1234567890',
            operator_name='Operator Name',
            company_name='Test Company',
            issue_date='2024-01-01',
            expiry_date='2029-01-01',
            remaining_months='12',
            trade='Trade',
            holo_gram_no='H-123',
            assessed_by='Assessor',
            status='Rejected',
            wasted_serial='XYZ123',
            requested_by='Requested By',
            prepared_by='Prepared By',
            invoice_no='INV-001',
            total_amount='100.00',
            amount='0.00',
            cash_bank='Bank',
            client_rep_name='Client Rep',
            client_rep_number='+966500000000',
            email='client@example.com',
            remarks='Rejected record',
            isReject=True,
            isApprove=False,
        )

    def test_rejected_cards_page_shows_delete_action_in_search_results(self):
        self.client.login(username='admin', password='TestPass123')

        response = self.client.get(reverse('rejected_cards'), {'searching_query': 'CARD-DELETE-001'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete this record')
        self.assertContains(response, 'data-bs-target="#deleteCardModal')

    def test_delete_rejected_card_removes_record(self):
        self.client.login(username='admin', password='TestPass123')

        response = self.client.post(
            reverse('delete_rejected_card', args=[self.card.uid]),
            {'next': reverse('rejected_cards')},
            follow=True,
        )

        self.assertRedirects(response, reverse('rejected_cards'))
        self.assertFalse(Card.objects.filter(pk=self.card.pk).exists())
        self.assertTrue(
            ActivityLog.objects.filter(
                user=self.user,
                action__icontains='Permanently deleted rejected card CARD-DELETE-001'
            ).exists()
        )
