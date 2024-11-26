import { Helmet } from 'react-helmet-async';
import { useSettingsContext } from '@/components/settings';
import ContractCompareView from '@/sections/dashboard/views/contract-compare-view';

import { Container } from '@mui/material';

// ----------------------------------------------------------------------

export default function ContractComparePage() {
  const settings = useSettingsContext();

  return (
    <>
      <Helmet>
        <title>Compare Contracts</title>
      </Helmet>

      <Container maxWidth={settings.themeStretch ? false : 'xl'}>
        <ContractCompareView />
      </Container>
    </>
  );
}
