import { Helmet } from 'react-helmet-async';
import { useSettingsContext } from '@/components/settings';

import { Container } from '@mui/material';

// ----------------------------------------------------------------------

export default function ContractIndexPage() {
  const settings = useSettingsContext();

  return (
    <>
      <Helmet>
        <title>Review</title>
      </Helmet>

      <Container maxWidth={settings.themeStretch ? false : 'xl'}>
      </Container>
    </>
  );
}
