import { Helmet } from 'react-helmet-async';
import { useSettingsContext } from '@/components/settings';
import AllReviewsView from '@/sections/dashboard/views/all-reviews-view';

import { Container } from '@mui/material';

// ----------------------------------------------------------------------
export default function ReviewsPage() {
  const settings = useSettingsContext();

  return (
    <>
      <Helmet>
        <title>All Reviews</title>
      </Helmet>

      <Container maxWidth={settings.themeStretch ? false : 'xl'}>
        <AllReviewsView />
      </Container>
    </>
  );
}
