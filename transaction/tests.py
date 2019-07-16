from datetime import datetime, date

from base.tests import JWTTestCase
from custom_auth import roles
from company.models import Company
from company.tests import CompanyTestMixin
from .models import Transaction, RecurringTransaction, TransactionTemplate
from . import views


class TransactionTestMixin(CompanyTestMixin):
    def setUp(self):
        super().setUp()
        self.company = self.create_company()

    def create_transaction(self, date=None, company=None, recurring_transaction=None, money=None,
                           type=None, description=None, notes=None, save=True):
        transaction = Transaction(date=(date or self.date), company=(company or self.company),
                                  recurring_transaction=(recurring_transaction or self.recurring_transaction),
                                  money=(money or self.money), type=(type or self.type),
                                  description=(description or self.description), notes=(notes or self.notes))
        if save:
            transaction.save()
        return transaction


class TransactionAllTestCase(TransactionTestMixin, JWTTestCase):
    def setUp(self):
        super().setUp()
        self.set_role(self.company, self.user, roles.REPORTER)
        self.date = datetime(2017, 5, 17)
        self.type = 'IN'
        self.money = '3000'
        self.description = '11th income.'
        self.notes = 'Incomes are cool.'
        self.recurring_transaction = None

    def test_no_login(self):
        response = self.get(views.TransactionAllView, {'limit': 3, 'offset': 0})
        self.assertEquals(response.status_code, 401, msg=response.content)

    def test_no_transactions(self):
        self.force_login(self.user)

        response = self.get(views.TransactionAllView, {'limit': 3, 'offset': 0})
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertIsNone(response.data['next'], msg=response.content)
        self.assertIsNone(response.data['previous'], msg=response.content)
        self.assertEquals(response.data['results'], [], msg=response.content)

    def test_one_page_transactions_ordered_by_date(self):
        self.force_login(self.user)
        tr1 = self.create_transaction(date=datetime(2022, 2, 22), description='second')
        tr2 = self.create_transaction(description='first')

        response = self.get(views.TransactionAllView, {'limit': 3, 'offset': 0})
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertIsNone(response.data['next'], msg=response.content)
        self.assertIsNone(response.data['previous'], msg=response.content)
        self.assertEquals(response.data['results'][0]['description'], tr2.description, msg=response.content)
        self.assertEquals(response.data['results'][1]['description'], tr1.description, msg=response.content)

    def test_three_pages_transactions(self):
        self.force_login(self.user)
        tr_first = self.create_transaction(date=datetime(2016, 4, 16), description='first')
        for i in range(6):
            self.create_transaction()
        tr_last = self.create_transaction(date=datetime(2018, 11, 9), description='last')
        tr_not = self.create_transaction(company=Company.objects.create(name='Other', org_nr='648587782428'))
        response_set = []

        response = self.get(views.TransactionAllView, {'limit': 3, 'offset': 0})
        self.assertEquals(response.status_code, 200, msg=response.content)
        response_set.extend(response.data['results'])
        next_url = response.data['next']
        self.assertIsNotNone(next_url, msg=response.content)
        self.assertIn(f'company_id={self.company.pk}', next_url)
        self.assertIn('limit=3', next_url)
        self.assertIn('offset=3', next_url)
        self.assertIsNone(response.data['previous'], msg=response.content)
        self.assertEquals(response.data['results'][0]['description'], tr_first.description, msg=response.content)

        # Follow link to next page
        response = self.get(views.TransactionAllView, url=response.data['next'])
        self.assertEquals(response.status_code, 200, msg=response.content)
        response_set.extend(response.data['results'])
        next_url = response.data['next']
        prev_url = response.data['previous']
        self.assertIsNotNone(next_url, msg=response.content)
        self.assertIsNotNone(prev_url, msg=response.content)
        self.assertIn(f'company_id={self.company.pk}', next_url)
        self.assertIn('limit=3', next_url)
        self.assertIn('offset=6', next_url)
        self.assertIn(f'company_id={self.company.pk}', prev_url)
        self.assertIn('limit=3', prev_url)
        self.assertEquals(len(response.data['results']), 3, msg=response.content)

        # Check that link back is to first page if 'offset=0' is added
        url_first = response.data['previous'] + '&offset=0'
        response_first = self.get(views.TransactionAllView, url=url_first)
        self.assertEquals(response_first.status_code, 200, msg=response_first.content)
        self.assertEquals(response_first.data['results'][0]['description'],
                          tr_first.description, msg=response_first.content)
        self.assertEquals(len(response_first.data['results']), 3, msg=response_first.content)

        # Check that link back when 'offset='1' is added does not contain first element
        url_back = response.data['previous'] + '&offset=1'
        response_back = self.get(views.TransactionAllView, url=url_back)
        self.assertEquals(response_back.status_code, 200, msg=response_back.content)
        self.assertNotIn(tr_first, response_back.data['results'], msg=response_back.content)
        self.assertEquals(len(response_back.data['results']), 3, msg=response_back.content)

        # Follow link to last page
        response = self.get(views.TransactionAllView, url=response.data['next'])
        self.assertEquals(response.status_code, 200, msg=response.content)
        response_set.extend(response.data['results'])
        self.assertIsNone(response.data['next'], msg=response.content)
        prev_url = response.data['previous']
        self.assertIsNotNone(prev_url, msg=response.content)
        self.assertIn(f'company_id={self.company.pk}', prev_url)
        self.assertIn('limit=3', prev_url)
        self.assertIn('offset=3', prev_url)
        self.assertEquals(len(response.data['results']), 2, msg=response.content)
        self.assertEquals(response.data['results'][1]['description'], tr_last.description, msg=response.content)
        self.assertNotIn(tr_not, response_set, msg=response.content)


class RecurringTransactionTestMixin(TransactionTestMixin):
    def create_recurring(self, start_date=None, end_date=None, day_delta=0, month_delta=0,
                         company=None, money=None, type=None, description='Test', notes='', save=True):
        template = TransactionTemplate.objects.create(money=money or self.money, description=description,
                                                      notes=notes, type=type or self.type)
        recurring = RecurringTransaction(start_date=start_date, end_date=end_date, day_delta=day_delta,
                                         month_delta=month_delta, company=(company or self.company), template=template)
        if save:
            recurring.save()
        return recurring


class RecurringTransactionTestCase(RecurringTransactionTestMixin, JWTTestCase):
    def setUp(self):
        super().setUp()
        # These values don't matter for the tests, so we just set defaults
        self.type = Transaction.INCOME
        self.money = 1000
        self.description = ''
        self.notes = ''

    def test_get_in_date_range(self):
        recurring = self.create_recurring(start_date=date(2018, 1, 1), end_date=date(2018, 1, 8), day_delta=2)

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 1), date(2018, 1, 7)),
            [date(2018, 1, 1), date(2018, 1, 3), date(2018, 1, 5), date(2018, 1, 7)]
        )

        self.assertEqual(
            recurring.get_occurences(date(2017, 12, 1), date(2018, 3, 8)),
            [date(2018, 1, 1), date(2018, 1, 3), date(2018, 1, 5), date(2018, 1, 7)]
        )

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 2), date(2018, 1, 6)),
            [date(2018, 1, 3), date(2018, 1, 5)]
        )

        self.create_transaction(date=date(2018, 1, 5), recurring_transaction=recurring)

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 1), date(2018, 1, 7)),
            [date(2018, 1, 1), date(2018, 1, 3), date(2018, 1, 5), date(2018, 1, 7)]
        )

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 1), date(2018, 1, 7), include_created=False),
            [date(2018, 1, 1), date(2018, 1, 3), date(2018, 1, 7)]
        )

    def test_get_in_month_range(self):
        recurring = self.create_recurring(start_date=date(2018, 1, 1), end_date=date(2019, 1, 1), month_delta=3)

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 1), date(2019, 1, 1)),
            [date(2018, 1, 1), date(2018, 4, 1), date(2018, 7, 1), date(2018, 10, 1), date(2019, 1, 1)]
        )

        self.assertEqual(
            recurring.get_occurences(date(2018, 1, 1), date(2018, 1, 30)),
            [date(2018, 1, 1)]
        )

        self.assertEqual(
            recurring.get_occurences(date(2017, 1, 1), date(2020, 1, 1)),
            [date(2018, 1, 1), date(2018, 4, 1), date(2018, 7, 1), date(2018, 10, 1), date(2019, 1, 1)]
        )

    def test_get_all_occurrences(self):
        daily_recurring = self.create_recurring(start_date=date(2018, 1, 1),
                                                end_date=date(2019, 1, 1),
                                                day_delta=14)
        monthly_recurring = self.create_recurring(start_date=date(2017, 12, 1),
                                                  end_date=date(2019, 1, 1),
                                                  month_delta=1)

        self.assertEqual(
            RecurringTransaction.get_all_occurences(self.company, date(2018, 1, 1), date(2018, 3, 1)),
            [
                (daily_recurring, [date(2018, 1, 1), date(2018, 1, 15), date(2018, 1, 29),
                                   date(2018, 2, 12), date(2018, 2, 26)]),
                (monthly_recurring, [date(2018, 1, 1), date(2018, 2, 1), date(2018, 3, 1)]),

            ]
        )
