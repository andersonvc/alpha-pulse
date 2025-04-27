'''
    async def get_latest_filings(self, limit: int = 40, filing_type: str = '8-K') -> pd.DataFrame:
        """Retrieves the latest filings from the SEC.
        
        Args:
            limit: Maximum number of filings to return (default: 40)
            filing_type: Type of filing to retrieve (default: '8-K')
            
        Returns:
            DataFrame containing filing information
        """
        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&owner=include&count={limit}&action=getcurrent&output=atom"
        resp = await self.client._make_request(url, self.client.headers)
        df = parse_atom_latest_filings_feed(resp)
        filtered_df = filter_8k_feed_by_items(df)

        # Get URLs and text content
        extracted_urls = await asyncio.gather(*[
            self._get_8k_urls(url) for url in filtered_df['base_url']
        ])
        filtered_df[['url_8k', 'url_ex99']] = pd.DataFrame([
            url.model_dump() for url in extracted_urls
        ])[['url_8k', 'url_ex99']]

        filtered_df['url_text'] = await asyncio.gather(*[
            self._get_url_text(url) for url in filtered_df['url_8k']
        ])
        return filtered_df
'''